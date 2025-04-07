package middleware

import (
	"FundAIHub/internal/auth"
	"FundAIHub/internal/device"
	"context"
	"encoding/json"
	"log"
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
	log.Printf("[AuthMiddleware] Responding with error: Code=%d, Message=%s", code, message)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(ErrorResponse{
		Error: message,
		Code:  code,
	})
}

func (m *AuthMiddleware) ValidateToken(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		log.Printf("[AuthMiddleware] Validating token for request: %s %s", r.Method, r.URL.Path)

		// 1. Extract and validate auth header
		authHeader := r.Header.Get("Authorization")
		if authHeader == "" {
			log.Println("[AuthMiddleware] Error: No authorization header found.")
			m.respondWithError(w, http.StatusUnauthorized, "No authorization header")
			return
		}

		parts := strings.Split(authHeader, " ")
		if len(parts) != 2 || parts[0] != "Bearer" {
			log.Println("[AuthMiddleware] Error: Invalid authorization header format.")
			m.respondWithError(w, http.StatusUnauthorized, "Invalid authorization header format")
			return
		}
		token := parts[1]

		// 2. Get hardware ID using our new detector
		hardwareID, err := m.identifier.GetHardwareID()
		if err != nil {
			log.Printf("[AuthMiddleware] Error getting hardware ID: %v", err)
			m.respondWithError(w, http.StatusInternalServerError, "Failed to get hardware ID")
			return
		}
		log.Printf("[AuthMiddleware] Hardware ID for validation: %s", hardwareID)

		// 3. Verify token with FundaVault
		log.Printf("[AuthMiddleware] Attempting to verify token with FundaVault...")
		result, err := m.fundaVault.VerifyToken(token, hardwareID)

		if err != nil {
			log.Printf("[AuthMiddleware] Error calling FundaVault VerifyToken: %v", err)
			m.respondWithError(w, http.StatusUnauthorized, "Token verification failed: FundaVault communication error")
			return
		}

		log.Printf("[AuthMiddleware] FundaVault VerifyToken result: Valid=%t, Payload=%+v", result.Valid, result.Payload)

		if !result.Valid {
			log.Printf("[AuthMiddleware] Token deemed invalid by FundaVault.")
			m.respondWithError(w, http.StatusUnauthorized, "Invalid token")
			return
		}

		log.Printf("[AuthMiddleware] Token validated successfully for UserID: %s", result.Payload.UserID)

		// 4. Check subscription status
		if result.Payload.SubscriptionEnd != "" {
			endTime, parseErr := time.Parse(time.RFC3339, result.Payload.SubscriptionEnd)
			if parseErr != nil {
				log.Printf("[AuthMiddleware] Warning: Could not parse subscription end date '%s': %v", result.Payload.SubscriptionEnd, parseErr)
			} else if time.Now().After(endTime) {
				log.Printf("[AuthMiddleware] Access denied for UserID %s: Subscription ended at %s", result.Payload.UserID, endTime.String())
				m.respondWithError(w, http.StatusForbidden, "Subscription expired")
				return
			}
		}

		// 5. Create enriched context
		ctx := context.WithValue(r.Context(), "hardware_id", hardwareID)
		ctx = context.WithValue(ctx, "user_id", result.Payload.UserID)
		ctx = context.WithValue(ctx, "is_admin", result.Payload.IsAdmin)
		ctx = context.WithValue(ctx, "subscription_end", result.Payload.SubscriptionEnd)

		log.Printf("[AuthMiddleware] Proceeding to next handler for UserID: %s", result.Payload.UserID)

		// 6. Call next handler with enriched context
		next.ServeHTTP(w, r.WithContext(ctx))
	}
}

// AdminOnly middleware for admin-only routes
func (m *AuthMiddleware) AdminOnly(next http.HandlerFunc) http.HandlerFunc {
	return m.ValidateToken(func(w http.ResponseWriter, r *http.Request) {
		isAdminVal := r.Context().Value("is_admin")
		isAdmin, ok := isAdminVal.(bool)
		if !ok {
			log.Printf("[AuthMiddleware] Error: 'is_admin' value not found or not a boolean in context for AdminOnly check.")
			m.respondWithError(w, http.StatusInternalServerError, "Internal context error")
			return
		}

		if !isAdmin {
			userIDVal := r.Context().Value("user_id")
			log.Printf("[AuthMiddleware] Access denied for UserID %v: Admin access required for %s %s", userIDVal, r.Method, r.URL.Path)
			m.respondWithError(w, http.StatusForbidden, "Admin access required")
			return
		}
		next.ServeHTTP(w, r)
	})
}
