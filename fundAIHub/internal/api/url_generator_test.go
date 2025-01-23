package api

import (
	"FundAIHub/internal/db"
	"context"
	"testing"
	"time"

	"github.com/google/uuid"
)

func TestURLGenerator(t *testing.T) {
	// Setup
	store, cleanup := setupTestDB(t)
	defer cleanup()

	// Create test content
	content := &db.Content{
		Name:     "Test Content",
		Type:     "application",
		Version:  "1.0",
		FilePath: "/test/path",
		Size:     1024,
	}

	ctx := context.Background()
	err := store.Create(ctx, content)
	if err != nil {
		t.Fatalf("Failed to create test content: %v", err)
	}

	generator := NewURLGenerator(store)

	t.Run("Generate Valid URL", func(t *testing.T) {
		url, err := generator.GenerateURL(content.ID, time.Hour)
		if err != nil {
			t.Fatalf("Failed to generate URL: %v", err)
		}
		if url == "" {
			t.Error("Expected non-empty URL")
		}

		// Validate the generated URL
		if !generator.ValidateURL(url) {
			t.Error("Generated URL failed validation")
		}
	})

	t.Run("Invalid Content ID", func(t *testing.T) {
		invalidID := uuid.New()
		_, err := generator.GenerateURL(invalidID, time.Hour)
		if err == nil {
			t.Error("Expected error for invalid content ID")
		}
	})

	t.Run("URL Expiration", func(t *testing.T) {
		// Generate URL with very short expiration
		url, err := generator.GenerateURL(content.ID, time.Millisecond)
		if err != nil {
			t.Fatalf("Failed to generate URL: %v", err)
		}

		// Wait for expiration
		time.Sleep(time.Millisecond * 2)

		// URL should no longer be valid
		if generator.ValidateURL(url) {
			t.Error("URL should have expired")
		}
	})

	t.Run("URL Tampering", func(t *testing.T) {
		url, err := generator.GenerateURL(content.ID, time.Hour)
		if err != nil {
			t.Fatalf("Failed to generate URL: %v", err)
		}

		// Tamper with the URL
		tamperedURL := url + "tampered"

		// Validation should fail
		if generator.ValidateURL(tamperedURL) {
			t.Error("Tampered URL should not validate")
		}
	})
}
