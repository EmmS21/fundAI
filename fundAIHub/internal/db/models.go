package db

import (
	"database/sql"
	"time"

	"github.com/google/uuid"
)

type Content struct {
	ID          uuid.UUID      `json:"id"`
	Name        string         `json:"name"`
	Type        string         `json:"type"`
	Version     string         `json:"version"`
	Description string         `json:"description"`
	AppVersion  string         `json:"app_version"`
	ReleaseDate time.Time      `json:"release_date"`
	AppType     string         `json:"app_type"`
	FilePath    string         `json:"file_path"`
	Size        int            `json:"size"`
	StorageKey  sql.NullString `json:"storage_key"`
	ContentType sql.NullString `json:"content_type"`
	CreatedAt   time.Time      `json:"created_at"`
	UpdatedAt   time.Time      `json:"updated_at"`
}

type Download struct {
	ID              uuid.UUID  `json:"id"`
	DeviceID        uuid.UUID  `json:"device_id"`
	UserID          string     `json:"user_id"`
	ContentID       uuid.UUID  `json:"content_id"`
	Status          string     `json:"status"`
	BytesDownloaded int64      `json:"bytes_downloaded"`
	TotalBytes      int64      `json:"total_bytes"`
	StartedAt       time.Time  `json:"created_at"`
	LastUpdatedAt   time.Time  `json:"last_updated_at"`
	CompletedAt     *time.Time `json:"completed_at,omitempty"`
	ErrorMessage    *string    `json:"error_message,omitempty"`
	ResumePosition  int64      `json:"resume_position"`
}
