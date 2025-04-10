package api

import (
	"FundAIHub/internal/db"
	"bytes"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"time"

	"github.com/google/uuid"
)

type DownloadHandler struct {
	store        *db.ContentStore
	urlGenerator *URLGenerator
}

func NewDownloadHandler(store *db.ContentStore) *DownloadHandler {
	return &DownloadHandler{
		store:        store,
		urlGenerator: NewURLGenerator(store),
	}
}

// StartDownload initiates a new download
func (h *DownloadHandler) StartDownload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		ContentID string `json:"contentId"`
		Resume    bool   `json:"resume,omitempty"`
	}

	// It might also be useful to log the raw body first
	bodyBytes, _ := io.ReadAll(r.Body)
	r.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))                      // Restore the body for Decode
	log.Printf("[StartDownload] Received Raw Body: %s", string(bodyBytes)) // Optional raw body logging

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		log.Printf("[StartDownload] Error decoding request body: %v", err) // Log decoding errors
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// --- Add logging right here ---
	log.Printf("[StartDownload] Attempting to parse ContentID: [%s]", req.ContentID) // Log the exact string being parsed

	// This part expects the value to be a valid UUID string.
	contentID, err := uuid.Parse(req.ContentID)
	if err != nil {
		// Log the error from uuid.Parse
		log.Printf("[StartDownload] Error parsing ContentID '%s': %v", req.ContentID, err)
		http.Error(w, "Invalid content ID", http.StatusBadRequest)
		return
	}

	// Get hardware_id and user_id from middleware context
	log.Printf("[StartDownload] Getting context values for device and user") // Added log
	deviceID := r.Context().Value("device_id").(string)
	userID := r.Context().Value("user_id").(string)
	log.Printf("[StartDownload] Context values - DeviceID: %s, UserID: %s", deviceID, userID) // Added log

	// Convert deviceID string to UUID
	log.Printf("[StartDownload] Parsing DeviceID string to UUID: [%s]", deviceID) // Added log
	deviceUUID, err := uuid.Parse(deviceID)
	if err != nil {
		log.Printf("[StartDownload] Error parsing DeviceID '%s': %v", deviceID, err) // Log device ID parse error
		http.Error(w, "Invalid device ID", http.StatusBadRequest)
		return
	}
	log.Printf("[StartDownload] DeviceID parsed successfully: %s", deviceUUID.String()) // Added log

	download := &db.Download{
		DeviceID:  deviceUUID,
		UserID:    userID,
		ContentID: contentID, // Uses the parsed UUID
		Status:    "started",
	}
	log.Printf("[StartDownload] Creating download record: %+v", download) // Added log

	if err := h.store.CreateDownload(r.Context(), download); err != nil {
		log.Printf("[StartDownload] [Error] Failed to create download in DB: %v", err) // Clarified log source
		http.Error(w, "Failed to start download", http.StatusInternalServerError)
		return
	}

	log.Printf("[StartDownload] Download record created successfully. Sending response.") // Added log
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(download)
}

// UpdateStatus updates the status of an existing download
func (h *DownloadHandler) UpdateStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	downloadID := r.URL.Query().Get("id")
	log.Printf("[Debug] Received request to update download ID: %s", downloadID)

	if downloadID == "" {
		http.Error(w, "Missing download ID", http.StatusBadRequest)
		return
	}

	var update struct {
		Status          string  `json:"status"`
		BytesDownloaded int64   `json:"bytes_downloaded"`
		ErrorMessage    *string `json:"error_message,omitempty"`
	}

	if err := json.NewDecoder(r.Body).Decode(&update); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	id, err := uuid.Parse(downloadID)
	if err != nil {
		log.Printf("[Error] Failed to parse UUID: %v", err)
		http.Error(w, "Invalid download ID", http.StatusBadRequest)
		return
	}
	log.Printf("[Debug] Parsed UUID: %s", id)

	download, err := h.store.GetDownloadByID(r.Context(), id)
	if err != nil {
		log.Printf("[Error] Failed to find download: %v", err)
		http.Error(w, "Download not found", http.StatusNotFound)
		return
	}
	log.Printf("[Debug] Found download: %+v", download)

	download.Status = update.Status
	download.BytesDownloaded = update.BytesDownloaded
	download.ErrorMessage = update.ErrorMessage

	if err := h.store.UpdateDownload(r.Context(), download); err != nil {
		log.Printf("[Error] Failed to update download: %v", err)
		http.Error(w, "Failed to update download", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(download)
}

// GetHistory returns download history for the current device
func (h *DownloadHandler) GetHistory(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	deviceID := r.Context().Value("device_id").(string)
	deviceUUID, err := uuid.Parse(deviceID)

	if err != nil {
		http.Error(w, "Invalid device ID", http.StatusBadRequest)
		return
	}

	downloads, err := h.store.ListDownloadsByDeviceID(r.Context(), deviceUUID)
	if err != nil {
		log.Printf("[Error] Failed to get download history: %v", err)
		http.Error(w, "Failed to get download history", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(downloads)
}

func (h *DownloadHandler) GetDownloadURL(w http.ResponseWriter, r *http.Request) {
	log.Printf("[GetDownloadURL] Handler started for request: %s", r.URL.String()) // Added log

	if r.Method != http.MethodGet {
		log.Printf("[GetDownloadURL] Error: Method not allowed (%s)", r.Method) // Added log
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	contentID := r.URL.Query().Get("content_id")
	log.Printf("[GetDownloadURL] Attempting to get content_id from query: [%s]", contentID) // Added log
	if contentID == "" {
		log.Printf("[GetDownloadURL] Error: Missing content_id query parameter") // Added log
		http.Error(w, "Missing content ID", http.StatusBadRequest)
		return
	}

	log.Printf("[GetDownloadURL] Attempting to parse contentID string: [%s]", contentID) // Added log
	id, err := uuid.Parse(contentID)
	if err != nil {
		log.Printf("[GetDownloadURL] Error parsing contentID '%s': %v", contentID, err) // Added log
		http.Error(w, "Invalid content ID", http.StatusBadRequest)
		return
	}
	log.Printf("[GetDownloadURL] ContentID parsed successfully: %s", id.String()) // Added log

	// Generate URL with 1-hour expiration
	log.Printf("[GetDownloadURL] Calling urlGenerator.GenerateURL for ID: %s", id.String()) // Added log
	url, err := h.urlGenerator.GenerateURL(id, time.Hour)
	if err != nil {
		// This log already exists, but added context
		log.Printf("[GetDownloadURL] [Error] urlGenerator.GenerateURL failed: %v", err)
		http.Error(w, "Failed to generate download URL", http.StatusInternalServerError)
		return
	}
	log.Printf("[GetDownloadURL] urlGenerator.GenerateURL succeeded. URL: %s", url) // Added log

	response := map[string]string{
		"download_url": url,
		"expires_in":   "1h",
	}

	log.Printf("[GetDownloadURL] Sending success response: %+v", response) // Added log
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}
