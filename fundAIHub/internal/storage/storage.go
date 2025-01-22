package storage

import (
	"context"
	"io"
	"time"
)

// FileInfo represents metadata about a stored file
type FileInfo struct {
	Key         string
	Size        int64
	ContentType string
	UpdatedAt   time.Time
}

// StorageService defines operations for file storage
type StorageService interface {
	// Upload stores a file and returns its storage key
	Upload(ctx context.Context, file io.Reader, filename string, contentType string) (*FileInfo, error)

	// Download retrieves a file by its key
	Download(ctx context.Context, key string) (io.ReadCloser, *FileInfo, error)

	// Delete removes a file from storage
	Delete(ctx context.Context, key string) error

	// GetInfo returns metadata about a stored file
	GetInfo(ctx context.Context, key string) (*FileInfo, error)
}
