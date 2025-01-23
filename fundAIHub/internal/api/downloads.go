package api

import (
	"FundAIHub/internal/db"
	"encoding/json"
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
		ContentID string `json:"content_id"`
		Resume    bool   `json:"resume,omitempty"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	contentID, err := uuid.Parse(req.ContentID)
	if err != nil {
		http.Error(w, "Invalid content ID", http.StatusBadRequest)
		return
	}

	// Get hardware_id and user_id from middleware context
	deviceID := r.Context().Value("device_id").(string)
	userID := r.Context().Value("user_id").(string)

	// Convert deviceID string to UUID
	deviceUUID, err := uuid.Parse(deviceID)
	if err != nil {
		http.Error(w, "Invalid device ID", http.StatusBadRequest)
		return
	}

	download := &db.Download{
		DeviceID:  deviceUUID,
		UserID:    userID,
		ContentID: contentID,
		Status:    "started",
	}

	if err := h.store.CreateDownload(r.Context(), download); err != nil {
		log.Printf("[Error] Failed to create download: %v", err)
		http.Error(w, "Failed to start download", http.StatusInternalServerError)
		return
	}

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
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	contentID := r.URL.Query().Get("content_id")
	if contentID == "" {
		http.Error(w, "Missing content ID", http.StatusBadRequest)
		return
	}

	id, err := uuid.Parse(contentID)
	if err != nil {
		http.Error(w, "Invalid content ID", http.StatusBadRequest)
		return
	}

	// Generate URL with 1-hour expiration
	url, err := h.urlGenerator.GenerateURL(id, time.Hour)
	if err != nil {
		log.Printf("[Error] Failed to generate download URL: %v", err)
		http.Error(w, "Failed to generate download URL", http.StatusInternalServerError)
		return
	}

	response := map[string]string{
		"download_url": url,
		"expires_in":   "1h",
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}
