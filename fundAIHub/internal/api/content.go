package api

import (
	"FundAIHub/internal/db"
	"FundAIHub/internal/storage"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"

	"github.com/google/uuid"
)

type ContentHandler struct {
	store   *db.ContentStore
	storage storage.StorageService
}

func NewContentHandler(store *db.ContentStore, storage storage.StorageService) *ContentHandler {
	return &ContentHandler{store: store, storage: storage}
}

func (h *ContentHandler) List(w http.ResponseWriter, r *http.Request) {
	contents, err := h.store.List(r.Context())
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(contents)
}

func (h *ContentHandler) Create(w http.ResponseWriter, r *http.Request) {
	var content db.Content
	if err := json.NewDecoder(r.Body).Decode(&content); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	if err := h.store.Create(r.Context(), &content); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(content)
}

func (h *ContentHandler) Update(w http.ResponseWriter, r *http.Request) {
	var content db.Content
	if err := json.NewDecoder(r.Body).Decode(&content); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	if err := h.store.Update(r.Context(), &content); err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Content not found", http.StatusNotFound)
			return
		}
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(content)
}

func (h *ContentHandler) Delete(w http.ResponseWriter, r *http.Request) {
	// Extract ID from URL
	idStr := r.URL.Query().Get("id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		http.Error(w, "Invalid ID", http.StatusBadRequest)
		return
	}

	if err := h.store.Delete(r.Context(), id); err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Content not found", http.StatusNotFound)
			return
		}
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func (h *ContentHandler) UploadFile(w http.ResponseWriter, r *http.Request) {
	log.Printf("[Connection Start] RemoteAddr: %s", r.RemoteAddr)
	log.Printf("[Headers] Content-Length: %d, Content-Type: %s", r.ContentLength, r.Header.Get("Content-Type"))

	log.Printf("[Request] Content-Length: %d bytes", r.ContentLength)
	log.Printf("[Request] Transfer-Encoding: %s", r.TransferEncoding)

	// Read the first few bytes of the body to see what we're getting
	bodyBytes := make([]byte, 1024)
	n, err := r.Body.Read(bodyBytes)
	if err != nil && err != io.EOF {
		log.Printf("Error reading request body: %v", err)
		http.Error(w, "Failed to read request body", http.StatusBadRequest)
		return
	}
	log.Printf("First %d bytes of request body: %s", n, bodyBytes[:n])

	// Don't set Content-Type header here - let the multipart form set it
	if err := r.ParseMultipartForm(32 << 20); err != nil {
		log.Printf("Error parsing multipart form: %v", err)
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		log.Printf("Error getting form file: %v", err)
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	defer file.Close()

	log.Printf("File received: %s, size: %d", header.Filename, header.Size)

	// Upload file to storage
	log.Println("Attempting to upload file to storage")
	fileInfo, err := h.storage.Upload(r.Context(), file, header.Filename, header.Header.Get("Content-Type"))
	if err != nil {
		log.Printf("Storage upload error: %v", err)
		http.Error(w, "Failed to upload file: "+err.Error(), http.StatusInternalServerError)
		return
	}
	log.Printf("Successfully uploaded file to storage with key: %s", fileInfo.Key)

	// Create content record
	content := &db.Content{
		Name:        header.Filename,
		Type:        "file",
		Version:     "1.0",
		StorageKey:  fileInfo.Key,
		ContentType: fileInfo.ContentType,
		Size:        int(fileInfo.Size),
		FilePath:    fileInfo.Key, // Using storage key as file path
	}

	if err := h.store.Create(r.Context(), content); err != nil {
		log.Printf("Database error: %v", err)
		// Cleanup the uploaded file
		h.storage.Delete(r.Context(), fileInfo.Key)
		http.Error(w, "Failed to create content record: "+err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(content)
}

func (h *ContentHandler) DownloadFile(w http.ResponseWriter, r *http.Request) {
	// Extract content ID from URL
	idStr := r.URL.Query().Get("id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		http.Error(w, "Invalid ID", http.StatusBadRequest)
		return
	}

	// Get content metadata from database
	content, err := h.store.Get(r.Context(), id)
	if err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "Content not found", http.StatusNotFound)
			return
		}
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Get file from storage
	reader, info, err := h.storage.Download(r.Context(), content.StorageKey)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer reader.Close()

	// Set response headers
	w.Header().Set("Content-Type", content.ContentType)
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=%s", content.Name))
	w.Header().Set("Content-Length", fmt.Sprintf("%d", info.Size))

	// Stream file to response
	if _, err := io.Copy(w, reader); err != nil {
		log.Printf("Error streaming file: %v", err)
	}
}
