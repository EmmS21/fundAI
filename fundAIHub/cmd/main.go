package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path"
	"time"

	"FundAIHub/internal/api"
	"FundAIHub/internal/auth"
	"FundAIHub/internal/config"
	"FundAIHub/internal/db"
	"FundAIHub/internal/middleware"

	"github.com/joho/godotenv"
)

type FileInfo struct {
	Key         string
	Size        int64
	ContentType string
	UpdatedAt   time.Time
}

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
		client:     &http.Client{Timeout: 60 * time.Second},
	}
}

func (s *SupabaseStorage) Upload(ctx context.Context, file io.Reader, filename string, contentType string) (*FileInfo, error) {
	url := fmt.Sprintf("%s/storage/v1/object/%s/%s",
		s.projectURL,
		s.bucketName,
		path.Clean(filename))

	log.Printf("[Debug] Uploading to: %s", url)

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

	body, _ := io.ReadAll(resp.Body)
	log.Printf("[Debug] Response: %s", string(body))

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("upload failed: %s", resp.Status)
	}

	var response struct {
		Key string `json:"Key"`
		Id  string `json:"Id"`
	}
	if err := json.NewDecoder(bytes.NewReader(body)).Decode(&response); err != nil {
		return nil, fmt.Errorf("parsing response: %w", err)
	}

	return &FileInfo{
		Key:         response.Key,
		ContentType: contentType,
		UpdatedAt:   time.Now(),
	}, nil
}

func (s *SupabaseStorage) Download(ctx context.Context, key string) (io.ReadCloser, *FileInfo, error) {
	url := fmt.Sprintf("%s/storage/v1/object/%s/%s",
		s.projectURL,
		s.bucketName,
		path.Clean(key))

	log.Printf("[Debug] Downloading from: %s", url)

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
		return nil, nil, fmt.Errorf("download failed: %s", resp.Status)
	}

	info := &FileInfo{
		Key:         key,
		ContentType: resp.Header.Get("Content-Type"),
		UpdatedAt:   time.Now(),
	}

	return resp.Body, info, nil
}

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

func main() {
	if err := godotenv.Load(); err != nil {
		log.Printf("[Warning] Error loading .env file: %v", err)
	}

	// Load configuration
	cfg := config.GetConfig()

	// Log the environment and URL being used
	log.Printf("Running in %s mode", cfg.Environment)
	log.Printf("Using FundaVault URL: %s", cfg.FundaVaultURL)

	// Add database initialization
	dbConfig := db.Config{
		ConnectionURL: os.Getenv("DATABASE_URL"),
	}
	database, err := db.NewConnection(dbConfig)
	if err != nil {
		log.Fatal(err)
	}
	defer database.Close()

	store := db.NewContentStore(database)

	// Initialize storage (existing code)
	storage := NewSupabaseStorage(
		os.Getenv("SUPABASE_URL"),
		os.Getenv("SUPABASE_KEY"),
		"content",
	)

	log.Printf("[Debug] Initialized storage with URL: %s", os.Getenv("SUPABASE_URL"))

	// Initialize FundaVault client with config
	fundaVault := auth.NewFundaVaultClient(cfg)

	// Initialize auth middleware
	authMiddleware := middleware.NewAuthMiddleware(fundaVault)

	// Add download endpoints
	downloadHandler := api.NewDownloadHandler(store)
	http.HandleFunc("/api/downloads/start",
		authMiddleware.ValidateToken(downloadHandler.StartDownload))
	http.HandleFunc("/api/downloads/status",
		authMiddleware.ValidateToken(downloadHandler.UpdateStatus))
	http.HandleFunc("/api/downloads/history",
		authMiddleware.ValidateToken(downloadHandler.GetHistory))
	http.HandleFunc("/api/downloads/url",
		authMiddleware.ValidateToken(downloadHandler.GetDownloadURL))

	http.HandleFunc("/upload", func(w http.ResponseWriter, r *http.Request) {
		log.Printf("[Debug] Received upload request")

		file, header, err := r.FormFile("file")
		if err != nil {
			log.Printf("[Error] Reading form file: %v", err)
			http.Error(w, "Could not read file", http.StatusBadRequest)
			return
		}
		defer file.Close()

		log.Printf("[Debug] File: %s, Size: %d", header.Filename, header.Size)

		// Upload to Supabase
		fileInfo, err := storage.Upload(r.Context(), file, header.Filename, header.Header.Get("Content-Type"))
		if err != nil {
			log.Printf("[Error] Upload failed: %v", err)
			http.Error(w, "Upload failed", http.StatusInternalServerError)
			return
		}

		log.Printf("[Success] File uploaded: %s", fileInfo.Key)

		// After successful storage upload
		if err := store.Create(r.Context(), &db.Content{
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
		}); err != nil {
			log.Printf("[Error] Database insert failed: %v", err)
			storage.Delete(r.Context(), fileInfo.Key)
			http.Error(w, "Failed to create content record", http.StatusInternalServerError)
			return
		}

		// Return success response
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{
			"message": "File uploaded successfully",
			"key":     fileInfo.Key,
		})
	})

	http.HandleFunc("/download", func(w http.ResponseWriter, r *http.Request) {
		// Get the file key from query parameter
		key := r.URL.Query().Get("key")
		if key == "" {
			http.Error(w, "Missing file key", http.StatusBadRequest)
			return
		}

		log.Printf("[Debug] Attempting to download file: %s", key)

		// Get the file from Supabase
		reader, info, err := storage.Download(r.Context(), key)
		if err != nil {
			log.Printf("[Error] Download failed: %v", err)
			http.Error(w, "Download failed", http.StatusInternalServerError)
			return
		}
		defer reader.Close()

		// Set response headers
		w.Header().Set("Content-Type", info.ContentType)
		w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=%s", path.Base(key)))
		if info.Size > 0 {
			w.Header().Set("Content-Length", fmt.Sprintf("%d", info.Size))
		}

		// Stream the file to response
		if _, err := io.Copy(w, reader); err != nil {
			log.Printf("[Error] Streaming file failed: %v", err)
		}
	})

	http.HandleFunc("/api/content/list", func(w http.ResponseWriter, r *http.Request) {
		contents, err := store.List(r.Context())
		if err != nil {
			log.Printf("[Error] Failed to list content: %v", err)
			http.Error(w, "Failed to list content", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(contents)
	})

	log.Printf("Server starting on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
