package api

import (
	"FundAIHub/internal/db"
	"FundAIHub/internal/storage"
	"bytes"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/google/uuid"
)

type DownloadHandler struct {
	store        *db.ContentStore
	urlGenerator *URLGenerator
	storage      storage.StorageService
}

func NewDownloadHandler(store *db.ContentStore, storage storage.StorageService) *DownloadHandler {
	return &DownloadHandler{
		store:        store,
		urlGenerator: NewURLGenerator(store),
		storage:      storage,
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

func (h *DownloadHandler) HandleSignedDownload(w http.ResponseWriter, r *http.Request) {
	log.Printf("[HandleSignedDownload] Received request for: %s", r.URL.RequestURI())

	// 1. Validate the signed URL
	isValid := h.urlGenerator.ValidateURL(r.URL.RequestURI())
	if !isValid {
		log.Printf("[HandleSignedDownload] Invalid or expired signature for: %s", r.URL.RequestURI())
		http.Error(w, "Forbidden: Invalid or expired download link", http.StatusForbidden)
		return
	}
	log.Printf("[HandleSignedDownload] URL signature validated successfully.")

	// 2. Extract the UUID from the path
	pathPrefix := "/download/"
	if !strings.HasPrefix(r.URL.Path, pathPrefix) {
		log.Printf("[HandleSignedDownload] Invalid path format: %s", r.URL.Path)
		http.Error(w, "Invalid download path", http.StatusBadRequest)
		return
	}
	uuidStr := strings.TrimPrefix(r.URL.Path, pathPrefix)
	contentID, err := uuid.Parse(uuidStr)
	if err != nil {
		log.Printf("[HandleSignedDownload] Could not parse UUID from path '%s': %v", uuidStr, err)
		http.Error(w, "Invalid content identifier in path", http.StatusBadRequest)
		return
	}
	log.Printf("[HandleSignedDownload] Extracted ContentID: %s", contentID.String())

	// 3. Get content metadata from the database
	content, err := h.store.Get(r.Context(), contentID)
	if err != nil {
		if err == sql.ErrNoRows {
			log.Printf("[HandleSignedDownload] Content not found in DB for ID: %s", contentID.String())
			http.Error(w, "Content not found", http.StatusNotFound)
			return
		}
		// Log the specific SQL scan error we encountered previously
		log.Printf("[HandleSignedDownload] Error fetching/scanning content metadata from DB: %v", err)
		http.Error(w, "Failed to retrieve content information", http.StatusInternalServerError)
		return
	}
	log.Printf("[HandleSignedDownload] Found content metadata: %+v", content)

	// 4. Check if StorageKey is valid and not NULL, then get the actual file stream
	if !content.StorageKey.Valid {
		log.Printf("[HandleSignedDownload] Error: Content record for ID %s has NULL or invalid StorageKey", contentID.String())
		http.Error(w, "Internal Server Error: Missing storage reference for content", http.StatusInternalServerError)
		return
	}
	storageKey := content.StorageKey.String // Get the actual string value
	log.Printf("[HandleSignedDownload] Attempting to download from storage with key: %s", storageKey)
	reader, info, err := h.storage.Download(r.Context(), storageKey)
	if err != nil {
		log.Printf("[HandleSignedDownload] Error downloading file from storage key '%s': %v", storageKey, err)
		http.Error(w, "Failed to access storage", http.StatusInternalServerError)
		return
	}
	defer reader.Close()
	log.Printf("[HandleSignedDownload] Successfully opened stream from storage. Info: %+v", info)

	// 5. Set response headers
	responseContentType := "application/octet-stream" // Default if NULL
	if content.ContentType.Valid {
		responseContentType = content.ContentType.String
	}
	w.Header().Set("Content-Type", responseContentType)
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=\"%s\"", content.Name))
	if info != nil && info.Size > 0 {
		w.Header().Set("Content-Length", fmt.Sprintf("%d", info.Size))
	} else if content.Size > 0 {
		w.Header().Set("Content-Length", fmt.Sprintf("%d", content.Size))
	}
	log.Printf("[HandleSignedDownload] Set download headers.")

	// 6. Stream the file content
	log.Printf("[HandleSignedDownload] Starting file stream to client...")
	bytesCopied, err := io.Copy(w, reader)
	if err != nil {
		log.Printf("[HandleSignedDownload] Error streaming file to client: %v", err)
		return
	}
	log.Printf("[HandleSignedDownload] Finished streaming %d bytes.", bytesCopied)
}
