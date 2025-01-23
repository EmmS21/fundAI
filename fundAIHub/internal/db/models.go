package db

import (
	"time"

	"github.com/google/uuid"
)

type Content struct {
	ID          uuid.UUID `json:"id"`
	Name        string    `json:"name"`
	Type        string    `json:"type"`
	Version     string    `json:"version"`
	Description string    `json:"description"`
	AppVersion  string    `json:"app_version"`
	ReleaseDate time.Time `json:"release_date"`
	AppType     string    `json:"app_type"`
	FilePath    string    `json:"file_path"`
	Size        int       `json:"size"`
	StorageKey  string    `json:"storage_key"`
	ContentType string    `json:"content_type"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}
