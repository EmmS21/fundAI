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
	Upload(ctx context.Context, file io.Reader, filename string, contentType string) (*FileInfo, error)
	Download(ctx context.Context, key string) (io.ReadCloser, *FileInfo, error)
	Delete(ctx context.Context, key string) error
	GetInfo(ctx context.Context, key string) (*FileInfo, error)
	ListFiles(ctx context.Context) ([]FileInfo, error)
}
