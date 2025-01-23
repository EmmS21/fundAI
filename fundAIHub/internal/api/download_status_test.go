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

	"github.com/google/uuid"
)

// Helper functions needed by the test
func setupTestDB(t *testing.T) (*db.ContentStore, func()) {
	dbURL := os.Getenv("DATABASE_URL")
	if dbURL == "" {
		t.Skip("Skipping test: DATABASE_URL not set")
	}

	dbConn, err := db.NewConnection(db.Config{
		ConnectionURL: dbURL,
	})
	if err != nil {
		t.Fatalf("Failed to connect to test database: %v", err)
	}

	store := db.NewContentStore(dbConn)

	cleanup := func() {
		dbConn.Close()
	}

	return store, cleanup
}

func createTestDownload(t *testing.T) *db.Download {
	store, cleanup := setupTestDB(t)
	defer cleanup()

	download := &db.Download{
		DeviceID:  uuid.New(),
		UserID:    "test-user",
		ContentID: uuid.New(),
		Status:    "started",
	}

	err := store.CreateDownload(context.Background(), download)
	if err != nil {
		t.Fatalf("Failed to create test download: %v", err)
	}

	return download
}

func updateDownloadStatus(t *testing.T, handler *DownloadHandler, id uuid.UUID, body map[string]interface{}) map[string]interface{} {
	bodyBytes, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("Failed to marshal body: %v", err)
	}

	req := httptest.NewRequest("PUT", "/api/downloads/status?id="+id.String(), bytes.NewBuffer(bodyBytes))
	req.Header.Set("Content-Type", "application/json")

	rr := httptest.NewRecorder()

	// Add required context values
	ctx := context.WithValue(req.Context(), "device_id", id.String())
	req = req.WithContext(ctx)

	handler.UpdateStatus(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("Handler returned wrong status code: got %v want %v", rr.Code, http.StatusOK)
	}

	var response map[string]interface{}
	if err := json.NewDecoder(rr.Body).Decode(&response); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	return response
}

func TestDownloadStatusUpdates(t *testing.T) {
	store, cleanup := setupTestDB(t)
	defer cleanup()

	// Create test content
	content := &db.Content{
		Name:     "Test Content",
		Type:     "test",
		Version:  "1.0",
		FilePath: "/test/path",
		Size:     1024,
	}

	err := store.Create(context.Background(), content)
	if err != nil {
		t.Fatalf("Failed to create test content: %v", err)
	}

	// Create a handler that will be used throughout the test
	handler := NewDownloadHandler(store)

	t.Run("Update to Completed", func(t *testing.T) {
		// Create download using the same store
		download := &db.Download{
			DeviceID:  uuid.New(),
			UserID:    "test-user",
			ContentID: content.ID,
			Status:    "started",
		}

		err := store.CreateDownload(context.Background(), download)
		if err != nil {
			t.Fatalf("Failed to create test download: %v", err)
		}

		// Update using the same handler
		body := map[string]interface{}{
			"status":           "completed",
			"bytes_downloaded": 1024,
		}

		response := updateDownloadStatus(t, handler, download.ID, body)

		if response["status"] != "completed" {
			t.Errorf("Expected status 'completed', got %v", response["status"])
		}
	})

	t.Run("Update to Paused", func(t *testing.T) {
		// Create another download with the same content
		download := &db.Download{
			DeviceID:  uuid.New(),
			UserID:    "test-user",
			ContentID: content.ID, // Use the same content
			Status:    "started",
		}

		err := store.CreateDownload(context.Background(), download)
		if err != nil {
			t.Fatalf("Failed to create test download: %v", err)
		}

		body := map[string]interface{}{
			"status":           "paused",
			"bytes_downloaded": 512,
		}

		response := updateDownloadStatus(t, handler, download.ID, body)

		if response["status"] != "paused" {
			t.Errorf("Expected status 'paused', got %v", response["status"])
		}
	})
}

func createTestContentForDownload(t *testing.T, store *db.ContentStore) uuid.UUID {
	content := &db.Content{
		Name:     "Test Content for Download",
		Type:     "test",
		Version:  "1.0",
		FilePath: "/test/path",
		Size:     1024,
	}

	err := store.Create(context.Background(), content)
	if err != nil {
		t.Fatalf("Failed to create test content: %v", err)
	}

	return content.ID
}
