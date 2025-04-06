package firebase_admin

import (
	"context"
	"fmt"
	"log"
	"os"
	"strings"

	"cloud.google.com/go/firestore"
	firebase "firebase.google.com/go/v4"
	"firebase.google.com/go/v4/auth"
	"firebase.google.com/go/v4/db"
	"firebase.google.com/go/v4/storage" // Import storage if needed later
	"google.golang.org/api/option"
)

// FirebaseAdminService defines the interface for interacting with Firebase Admin SDK.
type FirebaseAdminService interface {
	GetFirestoreClient(ctx context.Context) (*firestore.Clisent, error)
	GetAuthClient(ctx context.Context) (*auth.Client, error)
	GetDatabaseClient(ctx context.Context) (*db.Client, error)     // For Realtime Database
	GetStorageClient(ctx context.Context) (*storage.Client, error) // For Admin Storage access
	// Add other methods as needed for specific Firebase interactions
}

type firebaseAdminService struct {
	app *firebase.App
}

// NewFirebaseAdminService initializes the Firebase Admin SDK using environment variables.
func NewFirebaseAdminService(ctx context.Context) (FirebaseAdminService, error) {
	projectID := os.Getenv("FIREBASE_PROJECT_ID")
	clientEmail := os.Getenv("FIREBASE_CLIENT_EMAIL")
	privateKey := os.Getenv("FIREBASE_PRIVATE_KEY")

	if projectID == "" || clientEmail == "" || privateKey == "" {
		return nil, fmt.Errorf("FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL, and FIREBASE_PRIVATE_KEY environment variables must be set")
	}

	// Handle potential literal '\n' in the private key environment variable
	privateKey = strings.ReplaceAll(privateKey, "\\n", "\n")

	// Construct credentials JSON manually.
	// Note: You might need other fields from the original service account JSON
	// like private_key_id and client_id depending on specific SDK usage,
	// but ProjectID, ClientEmail, and PrivateKey are often sufficient for initialization.
	// Storing the entire JSON content in a single env variable (e.g., FIREBASE_CREDENTIALS_JSON)
	// and using option.WithCredentialsJSON is generally more robust.
	credentialsJSON := fmt.Sprintf(`{
      "type": "service_account",
      "project_id": "%s",
      "private_key": "%s",
      "client_email": "%s",
      "token_uri": "https://oauth2.googleapis.com/token"
    }`, projectID, privateKey, clientEmail)

	opt := option.WithCredentialsJSON([]byte(credentialsJSON))

	// Initialize the app
	config := &firebase.Config{ProjectID: projectID}
	app, err := firebase.NewApp(ctx, config, opt)
	if err != nil {
		return nil, fmt.Errorf("error initializing Firebase app: %w", err)
	}

	log.Println("Firebase Admin SDK initialized successfully for project:", projectID)
	return &firebaseAdminService{app: app}, nil
}

// GetFirestoreClient returns a Firestore client.
func (s *firebaseAdminService) GetFirestoreClient(ctx context.Context) (*firestore.Client, error) {
	client, err := s.app.Firestore(ctx)
	if err != nil {
		return nil, fmt.Errorf("error getting Firestore client: %w", err)
	}
	return client, nil
}

// GetAuthClient returns an Auth client.
func (s *firebaseAdminService) GetAuthClient(ctx context.Context) (*auth.Client, error) {
	client, err := s.app.Auth(ctx)
	if err != nil {
		return nil, fmt.Errorf("error getting Auth client: %w", err)
	}
	return client, nil
}

// GetDatabaseClient returns a Realtime Database client.
func (s *firebaseAdminService) GetDatabaseClient(ctx context.Context) (*db.Client, error) {
	client, err := s.app.Database(ctx)
	if err != nil {
		return nil, fmt.Errorf("error getting Realtime Database client: %w", err)
	}
	return client, nil
}

// GetStorageClient returns a Cloud Storage client associated with the default bucket.
func (s *firebaseAdminService) GetStorageClient(ctx context.Context) (*storage.Client, error) {
	client, err := s.app.Storage(ctx)
	if err != nil {
		return nil, fmt.Errorf("error getting Storage client: %w", err)
	}
	return client, nil
}
