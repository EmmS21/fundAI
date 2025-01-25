package middleware

import (
	"FundAIHub/internal/auth"
	"context"
	"net/http"
	"strings"
)

type AuthMiddleware struct {
	fundaVault *auth.FundaVaultClient
}

func NewAuthMiddleware(fundaVault *auth.FundaVaultClient) *AuthMiddleware {
	return &AuthMiddleware{
		fundaVault: fundaVault,
	}
}

func (m *AuthMiddleware) ValidateToken(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		authHeader := r.Header.Get("Authorization")
		if authHeader == "" {
			http.Error(w, "No authorization header", http.StatusUnauthorized)
			return
		}

		// Extract token
		parts := strings.Split(authHeader, " ")
		if len(parts) != 2 || parts[0] != "Bearer" {
			http.Error(w, "Invalid authorization header", http.StatusUnauthorized)
			return
		}
		token := parts[1]

		// Get hardware ID from header
		hardwareID := r.Header.Get("Device-ID")

		// Verify token
		result, err := m.fundaVault.VerifyToken(token, hardwareID)
		if err != nil {
			http.Error(w, "Token verification failed", http.StatusUnauthorized)
			return
		}

		if !result.Valid {
			http.Error(w, "Invalid token", http.StatusUnauthorized)
			return
		}

		// Add verified claims to request context
		ctx := r.Context()
		ctx = context.WithValue(ctx, "user_claims", result.Payload)
		next.ServeHTTP(w, r.WithContext(ctx))
	}
}
