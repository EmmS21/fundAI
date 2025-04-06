package api

import (
	"FundAIHub/internal/firebase_admin"
	"encoding/json"
	"log"
	"net/http"
)

// FirebaseHandler handles API requests related to Firebase admin operations.
type FirebaseHandler struct {
	firebaseService firebase_admin.FirebaseAdminService
	// Add other dependencies like the User Store if needed
}

// NewFirebaseHandler creates a new FirebaseHandler.
func NewFirebaseHandler(fbService firebase_admin.FirebaseAdminService) *FirebaseHandler {
	return &FirebaseHandler{
		firebaseService: fbService,
	}
}

// HandleSecureFirestoreWrite is a placeholder for writing data to Firestore using admin privileges.
// It expects authentication via middleware.
func (h *FirebaseHandler) HandleSecureFirestoreWrite(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context() // Use request context

	// --- Authentication should be handled by middleware before this point ---
	// You might extract user info from context if middleware adds it:
	// userID := ctx.Value("userID").(string) // Example

	// Example: Decode request body (adjust based on actual data needed)
	var requestData map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&requestData); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}
	log.Printf("[Firebase Handler] Received data: %+v", requestData)

	// Get Firestore client
	client, err := h.firebaseService.GetFirestoreClient(ctx)
	if err != nil {
		log.Printf("[Error] Getting Firestore client: %v", err)
		http.Error(w, "Internal server error (Firestore init)", http.StatusInternalServerError)
		return
	}
	defer client.Close() // Ensure client is closed

	// Example: Write data to a specific document (replace with actual logic)
	// This demonstrates using admin privileges to write, potentially bypassing security rules.
	docRef := client.Collection("secureData").Doc("exampleDoc")
	_, err = docRef.Set(ctx, requestData)
	if err != nil {
		log.Printf("[Error] Writing to Firestore: %v", err)
		http.Error(w, "Failed to write data", http.StatusInternalServerError)
		return
	}

	log.Printf("[Firebase Handler] Successfully wrote data to Firestore path: %s", docRef.Path)

	// Send success response
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"message": "Data written successfully"})
}
