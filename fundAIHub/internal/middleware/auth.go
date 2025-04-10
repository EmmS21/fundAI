package middleware

import (
	"FundAIHub/internal/auth"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"
)

type AuthMiddleware struct {
	fundaVault *auth.FundaVaultClient
}

type ErrorResponse struct {
	Error string `json:"error"`
	Code  int    `json:"code"`
}

func NewAuthMiddleware(fundaVault *auth.FundaVaultClient) *AuthMiddleware {
	return &AuthMiddleware{
		fundaVault: fundaVault,
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

func (m *AuthMiddleware) AuthenticateDevice(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		log.Printf("[AuthMiddleware] Authenticating device for request: %s %s", r.Method, r.URL.Path)

		// 1. Extract Device-ID header
		hardwareID := r.Header.Get("Device-ID")
		if hardwareID == "" {
			log.Println("[AuthMiddleware] Error: Missing Device-ID header.")
			m.respondWithError(w, http.StatusUnauthorized, "Missing Device-ID header")
			return
		}

		// 2. Verify device with FundaVault
		log.Printf("[AuthMiddleware] Attempting to verify Device-ID '%s' with FundaVault...", hardwareID)
		result, statusCode, err := m.fundaVault.VerifyDevice(hardwareID)

		if err != nil {
			log.Printf("[AuthMiddleware] FundaVault verification returned error: %v (StatusCode: %d)", err, statusCode)

			switch statusCode {
			case http.StatusNotFound:
				m.respondWithError(w, http.StatusUnauthorized, "Device not registered")
			case http.StatusForbidden:
				m.respondWithError(w, http.StatusForbidden, "Device or user inactive, or subscription expired")
			case http.StatusConflict:
				m.respondWithError(w, http.StatusForbidden, "Verification conflict")
			case http.StatusInternalServerError:
				m.respondWithError(w, http.StatusServiceUnavailable, "Authentication service error")
			case 0:
				fallthrough
			default:
				m.respondWithError(w, http.StatusServiceUnavailable, "Authentication service unavailable")
			}
			return
		}

		if statusCode != http.StatusOK || result == nil || !result.Authenticated {
			log.Printf("[AuthMiddleware] Verification inconsistency: StatusCode=%d, ResultNil=%t, Authenticated=%t", statusCode, result == nil, result != nil && result.Authenticated)
			m.respondWithError(w, http.StatusInternalServerError, "Internal authentication error")
			return
		}

		userIDStr := fmt.Sprintf("%d", result.UserID)
		log.Printf("[AuthMiddleware] Device '%s' validated successfully for UserID: %s (Email: %s)", hardwareID, userIDStr, result.Email)

		if result.SubscriptionEnd != "" {
			endTime, parseErr := time.Parse(time.RFC3339, result.SubscriptionEnd)
			if parseErr != nil {
				log.Printf("[AuthMiddleware] Warning: Could not parse subscription end date '%s' from FundaVault payload: %v", result.SubscriptionEnd, parseErr)
			} else if time.Now().After(endTime) {
				log.Printf("[AuthMiddleware] Access denied for UserID %s: Subscription ended at %s", userIDStr, endTime.String())
				m.respondWithError(w, http.StatusForbidden, "Subscription expired")
				return
			}
		}

		ctx := context.WithValue(r.Context(), "device_id", hardwareID)
		ctx = context.WithValue(ctx, "user_id", userIDStr)
		ctx = context.WithValue(ctx, "is_admin", result.IsAdmin)
		ctx = context.WithValue(ctx, "subscription_end", result.SubscriptionEnd)
		ctx = context.WithValue(ctx, "email", result.Email)

		log.Printf("[AuthMiddleware] Proceeding to next handler for UserID: %s", userIDStr)

		next.ServeHTTP(w, r.WithContext(ctx))
	}
}

func (m *AuthMiddleware) AdminOnly(next http.HandlerFunc) http.HandlerFunc {
	return m.AuthenticateDevice(func(w http.ResponseWriter, r *http.Request) {
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
