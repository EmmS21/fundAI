package api

import (
	"FundAIHub/internal/db"
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"fmt"
	"net/url"
	"strings"
	"time"

	"github.com/google/uuid"
)

type URLGenerator struct {
	store      *db.ContentStore
	signingKey []byte // Used for signing URLs
}

func NewURLGenerator(store *db.ContentStore) *URLGenerator {
	// In production, this should be loaded from environment/config
	key := []byte("your-secure-signing-key")
	return &URLGenerator{
		store:      store,
		signingKey: key,
	}
}

type URLParams struct {
	ContentID uuid.UUID
	ExpiresAt time.Time
	Signature string
}

func (g *URLGenerator) GenerateURL(contentID uuid.UUID, duration time.Duration) (string, error) {
	// Add context
	ctx := context.Background()

	// Use correct method name and pass context
	content, err := g.store.GetByID(ctx, contentID)
	if err != nil {
		return "", fmt.Errorf("content not found: %v", err)
	}

	// Use the content variable (to avoid unused variable error)
	if content.Size == 0 {
		return "", fmt.Errorf("invalid content: size is 0")
	}

	expiresAt := time.Now().Add(duration)

	// Create signature
	mac := hmac.New(sha256.New, g.signingKey)
	mac.Write([]byte(contentID.String()))
	mac.Write([]byte(expiresAt.UTC().Format(time.RFC3339)))
	signature := base64.URLEncoding.EncodeToString(mac.Sum(nil))

	// Generate URL with params
	url := fmt.Sprintf("/download/%s?expires=%s&signature=%s",
		contentID,
		expiresAt.UTC().Format(time.RFC3339),
		signature,
	)

	return url, nil
}

func (g *URLGenerator) ValidateURL(urlStr string) bool {
	// Parse URL path and query parameters
	parsedURL, err := url.Parse(urlStr)
	if err != nil {
		return false
	}

	// Extract contentID from path
	// URL format: /download/{contentID}?expires={timestamp}&signature={sig}
	pathParts := strings.Split(strings.Trim(parsedURL.Path, "/"), "/")
	if len(pathParts) != 2 || pathParts[0] != "download" {
		return false
	}

	contentID, err := uuid.Parse(pathParts[1])
	if err != nil {
		return false
	}

	// Get query parameters
	queryParams := parsedURL.Query()
	expiresStr := queryParams.Get("expires")
	receivedSignature := queryParams.Get("signature")

	if expiresStr == "" || receivedSignature == "" {
		return false
	}

	// Parse expiration time
	expiresAt, err := time.Parse(time.RFC3339, expiresStr)
	if err != nil {
		return false
	}

	// Check if URL has expired
	if time.Now().After(expiresAt) {
		return false
	}

	// Add context
	ctx := context.Background()

	// Use correct method name and pass context
	_, err = g.store.GetByID(ctx, contentID)
	if err != nil {
		return false
	}

	// Recreate signature for comparison
	mac := hmac.New(sha256.New, g.signingKey)
	mac.Write([]byte(contentID.String()))
	mac.Write([]byte(expiresAt.UTC().Format(time.RFC3339)))
	expectedSignature := base64.URLEncoding.EncodeToString(mac.Sum(nil))

	// Compare signatures
	return hmac.Equal(
		[]byte(receivedSignature),
		[]byte(expectedSignature),
	)
}
