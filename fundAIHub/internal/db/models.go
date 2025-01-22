package db

import (
	"time"

	"github.com/google/uuid"
)

type Content struct {
	ID        uuid.UUID `json:"id"`
	Name      string    `json:"name"`
	Type      string    `json:"type"`
	Version   string    `json:"version"`
	FilePath  string    `json:"file_path"`
	Size      int       `json:"size"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}
