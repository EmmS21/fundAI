package api

import (
	"FundAIHub/internal/db"
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"
)

// mockEduVaultMiddleware simulates the EduVault middleware for testing
func mockEduVaultMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// Simulate device verification
		deviceID := "test-device-" + time.Now().Format("20060102")
		userID := "test-user-" + time.Now().Format("20060102")

		// Add to context like EduVault would
		ctx := context.WithValue(r.Context(), "hardware_id", deviceID)
		ctx = context.WithValue(ctx, "user_id", userID)

		// Call the next handler with our test context
		next.ServeHTTP(w, r.WithContext(ctx))
	}
}

func TestDownloadFlow(t *testing.T) {
	dbURL := os.Getenv("DATABASE_URL")
	if dbURL == "" {
		t.Skip("Skipping test: DATABASE_URL not set")
	}

	// Setup test DB connection
	dbConn, err := db.NewConnection(db.Config{
		ConnectionURL: dbURL,
	})
	if err != nil {
		t.Fatalf("Failed to connect to test database: %v", err)
	}
	defer dbConn.Close()

	// Create store using the correct function
	store := db.NewContentStore(dbConn) // This is the correct function call
	handler := NewDownloadHandler(store)

	// Create test content first
	content := createTestContent(t, store)

	// Test starting a download
	t.Run("Start Download", func(t *testing.T) {
		body := map[string]interface{}{
			"content_id": content.ID.String(),
			"resume":     false,
		}

		bodyBytes, _ := json.Marshal(body)
		req := httptest.NewRequest("POST", "/api/downloads/start", bytes.NewBuffer(bodyBytes))
		req.Header.Set("Content-Type", "application/json")

		rr := httptest.NewRecorder()

		// Use mock middleware
		handlerFunc := mockEduVaultMiddleware(handler.StartDownload)
		handlerFunc.ServeHTTP(rr, req)

		if rr.Code != http.StatusOK {
			t.Errorf("handler returned wrong status code: got %v want %v",
				rr.Code, http.StatusOK)
		}

		// Parse response
		var response map[string]interface{}
		if err := json.NewDecoder(rr.Body).Decode(&response); err != nil {
			t.Fatalf("Failed to decode response: %v", err)
		}

		// Add assertions for response content
		if _, ok := response["id"]; !ok {
			t.Error("Expected download ID in response")
		}
	})

	// Add more test cases for status updates and history
}

// Helper function to create test content
func createTestContent(t *testing.T, store *db.ContentStore) *db.Content {
	content := &db.Content{
		Name:    "Test Content",
		Type:    "test",
		Version: "1.0",
		Size:    1024,
	}

	ctx := context.Background()
	if err := store.Create(ctx, content); err != nil {
		t.Fatalf("Failed to create test content: %v", err)
	}

	return content
}
