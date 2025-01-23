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
	log.Printf("[Debug] Starting file upload handler")

	// Parse form data
	if err := r.ParseMultipartForm(32 << 20); err != nil {
		http.Error(w, "Could not parse form", http.StatusBadRequest)
		return
	}

	// Get file
	file, header, err := r.FormFile("file")
	if err != nil {
		http.Error(w, "Could not read file", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// Upload to storage
	fileInfo, err := h.storage.Upload(r.Context(), file, header.Filename, header.Header.Get("Content-Type"))
	if err != nil {
		http.Error(w, "Upload failed", http.StatusInternalServerError)
		return
	}

	// Create content record with metadata
	content := &db.Content{
		Name:        header.Filename,
		Type:        "linux-app",
		Version:     r.FormValue("version"),
		Description: r.FormValue("description"),
		AppVersion:  r.FormValue("app_version"),
		AppType:     r.FormValue("app_type"),
		FilePath:    fileInfo.Key,
		Size:        int(header.Size),
		StorageKey:  fileInfo.Key,
		ContentType: header.Header.Get("Content-Type"),
	}

	// Automatically create/update database record
	if err := h.store.Create(r.Context(), content); err != nil {
		// If database insert fails, clean up the uploaded file
		h.storage.Delete(r.Context(), fileInfo.Key)
		http.Error(w, "Failed to create content record", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
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

// List all content
func (h *ContentHandler) ListContent(w http.ResponseWriter, r *http.Request) {
	contents, err := h.store.List(r.Context())
	if err != nil {
		log.Printf("[Error] Failed to list content: %v", err)
		http.Error(w, "Failed to list content", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(contents)
}

// Get content by ID
func (h *ContentHandler) GetContent(w http.ResponseWriter, r *http.Request) {
	idStr := r.URL.Query().Get("id")
	id, err := uuid.Parse(idStr)
	if err != nil {
		http.Error(w, "Invalid ID", http.StatusBadRequest)
		return
	}

	content, err := h.store.Get(r.Context(), id)
	if err != nil {
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
