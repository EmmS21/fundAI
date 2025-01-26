package middleware

import (
	"FundAIHub/internal/auth"
	"FundAIHub/internal/device"
	"context"
	"encoding/json"
	"net/http"
	"strings"
	"time"
)

type AuthMiddleware struct {
	fundaVault *auth.FundaVaultClient
	identifier device.DeviceIdentifier
}

type ErrorResponse struct {
	Error string `json:"error"`
	Code  int    `json:"code"`
}

func NewAuthMiddleware(fundaVault *auth.FundaVaultClient) *AuthMiddleware {
	return &AuthMiddleware{
		fundaVault: fundaVault,
		identifier: device.NewSystemIdentifier(),
	}
}

func (m *AuthMiddleware) respondWithError(w http.ResponseWriter, code int, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(ErrorResponse{
		Error: message,
		Code:  code,
	})
}

func (m *AuthMiddleware) ValidateToken(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// 1. Extract and validate auth header
		authHeader := r.Header.Get("Authorization")
		if authHeader == "" {
			m.respondWithError(w, http.StatusUnauthorized, "No authorization header")
			return
		}

		parts := strings.Split(authHeader, " ")
		if len(parts) != 2 || parts[0] != "Bearer" {
			m.respondWithError(w, http.StatusUnauthorized, "Invalid authorization header")
			return
		}
		token := parts[1]

		// 2. Get hardware ID using our new detector
		hardwareID, err := m.identifier.GetHardwareID()
		if err != nil {
			m.respondWithError(w, http.StatusInternalServerError, "Failed to get hardware ID")
			return
		}

		// 3. Verify token with FundaVault
		result, err := m.fundaVault.VerifyToken(token, hardwareID)
		if err != nil {
			m.respondWithError(w, http.StatusUnauthorized, "Token verification failed")
			return
		}

		if !result.Valid {
			m.respondWithError(w, http.StatusUnauthorized, "Invalid token")
			return
		}

		// 4. Check subscription status
		if result.Payload.SubscriptionEnd != "" {
			endTime, err := time.Parse(time.RFC3339, result.Payload.SubscriptionEnd)
			if err == nil && time.Now().After(endTime) {
				m.respondWithError(w, http.StatusForbidden, "Subscription expired")
				return
			}
		}

		// 5. Create enriched context
		ctx := context.WithValue(r.Context(), "hardware_id", hardwareID)
		ctx = context.WithValue(ctx, "user_id", result.Payload.UserID)
		ctx = context.WithValue(ctx, "is_admin", result.Payload.IsAdmin)
		ctx = context.WithValue(ctx, "subscription_end", result.Payload.SubscriptionEnd)

		// 6. Call next handler with enriched context
		next.ServeHTTP(w, r.WithContext(ctx))
	}
}

// AdminOnly middleware for admin-only routes
func (m *AuthMiddleware) AdminOnly(next http.HandlerFunc) http.HandlerFunc {
	return m.ValidateToken(func(w http.ResponseWriter, r *http.Request) {
		isAdmin := r.Context().Value("is_admin").(bool)
		if !isAdmin {
			m.respondWithError(w, http.StatusForbidden, "Admin access required")
			return
		}
		next.ServeHTTP(w, r)
	})
}
