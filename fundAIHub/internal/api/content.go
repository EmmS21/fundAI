package api

import (
	"FundAIHub/internal/db"
	"database/sql"
	"encoding/json"
	"net/http"

	"github.com/google/uuid"
)

type ContentHandler struct {
	store *db.ContentStore
}

func NewContentHandler(store *db.ContentStore) *ContentHandler {
	return &ContentHandler{store: store}
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
