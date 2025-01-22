package storage

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"path"
	"time"
)

type SupabaseStorage struct {
	projectURL string
	apiKey     string
	bucketName string
	client     *http.Client
}

func NewSupabaseStorage(projectURL, apiKey, bucketName string) *SupabaseStorage {
	return &SupabaseStorage{
		projectURL: projectURL,
		apiKey:     apiKey,
		bucketName: bucketName,
		client:     &http.Client{Timeout: 30 * time.Second},
	}
}

func (s *SupabaseStorage) Upload(ctx context.Context, file io.Reader, filename string, contentType string) (*FileInfo, error) {
	url := fmt.Sprintf("%s/storage/v1/object/%s/%s",
		s.projectURL,
		s.bucketName,
		path.Clean(filename))

	req, err := http.NewRequestWithContext(ctx, "POST", url, file)
	if err != nil {
		return nil, fmt.Errorf("creating request: %w", err)
	}

	req.Header.Set("Authorization", "Bearer "+s.apiKey)
	req.Header.Set("Content-Type", contentType)

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("uploading file: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("upload failed: %s", resp.Status)
	}

	return &FileInfo{
		Key:         filename,
		ContentType: contentType,
		UpdatedAt:   time.Now(),
	}, nil
}

// Download retrieves a file from storage
func (s *SupabaseStorage) Download(ctx context.Context, key string) (io.ReadCloser, *FileInfo, error) {
	url := fmt.Sprintf("%s/storage/v1/object/%s/%s",
		s.projectURL,
		s.bucketName,
		path.Clean(key))

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, nil, fmt.Errorf("creating request: %w", err)
	}

	req.Header.Set("Authorization", "Bearer "+s.apiKey)

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, nil, fmt.Errorf("downloading file: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		resp.Body.Close()
		return nil, nil, fmt.Errorf("download failed: %s", resp.Status)
	}

	info := &FileInfo{
		Key:         key,
		Size:        resp.ContentLength,
		ContentType: resp.Header.Get("Content-Type"),
		UpdatedAt:   time.Now(),
	}

	return resp.Body, info, nil
}

// Delete removes a file from storage
func (s *SupabaseStorage) Delete(ctx context.Context, key string) error {
	url := fmt.Sprintf("%s/storage/v1/object/%s/%s",
		s.projectURL,
		s.bucketName,
		path.Clean(key))

	req, err := http.NewRequestWithContext(ctx, "DELETE", url, nil)
	if err != nil {
		return fmt.Errorf("creating request: %w", err)
	}

	req.Header.Set("Authorization", "Bearer "+s.apiKey)

	resp, err := s.client.Do(req)
	if err != nil {
		return fmt.Errorf("deleting file: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("delete failed: %s", resp.Status)
	}

	return nil
}

// GetInfo retrieves file information from storage
func (s *SupabaseStorage) GetInfo(ctx context.Context, key string) (*FileInfo, error) {
	url := fmt.Sprintf("%s/storage/v1/object/info/%s/%s",
		s.projectURL,
		s.bucketName,
		path.Clean(key))

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("creating request: %w", err)
	}

	req.Header.Set("Authorization", "Bearer "+s.apiKey)

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("getting file info: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("getting info failed: %s", resp.Status)
	}

	return &FileInfo{
		Key:         key,
		Size:        resp.ContentLength,
		ContentType: resp.Header.Get("Content-Type"),
		UpdatedAt:   time.Now(),
	}, nil
}
