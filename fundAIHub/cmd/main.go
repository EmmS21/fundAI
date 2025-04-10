package main

import (
	"bytes"
	"context"
	"database/sql"
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
	"FundAIHub/internal/firebase_admin"
	"FundAIHub/internal/middleware"
	"FundAIHub/internal/storage"

	_ "github.com/joho/godotenv/autoload"
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

func (s *SupabaseStorage) Upload(ctx context.Context, file io.Reader, filename string, contentType string) (*storage.FileInfo, error) {
	uploadURL := fmt.Sprintf("%s/storage/v1/object/%s/%s", s.projectURL, s.bucketName, filename)
	req, err := http.NewRequestWithContext(ctx, "POST", uploadURL, file)
	if err != nil {
		return nil, fmt.Errorf("failed to create upload request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+s.apiKey)
	req.Header.Set("Content-Type", contentType)
	req.Header.Set("x-upsert", "true") // Overwrite if exists

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to execute upload request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("upload failed with status %d: %s", resp.StatusCode, string(bodyBytes))
	}

	log.Printf("[SupabaseStorage] Upload successful for %s. Status: %d", filename, resp.StatusCode)

	return &storage.FileInfo{
		Key:         filename,
		ContentType: contentType,
	}, nil
}

func (s *SupabaseStorage) Download(ctx context.Context, key string) (io.ReadCloser, *storage.FileInfo, error) {
	downloadURL := fmt.Sprintf("%s/storage/v1/object/authenticated/%s/%s", s.projectURL, s.bucketName, key)
	req, err := http.NewRequestWithContext(ctx, "GET", downloadURL, nil)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to create download request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+s.apiKey)

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to execute download request: %w", err)
	}

	if resp.StatusCode == http.StatusNotFound {
		resp.Body.Close()
		return nil, nil, fmt.Errorf("file not found in storage: %s", key)
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		return nil, nil, fmt.Errorf("download failed with status %d: %s", resp.StatusCode, string(bodyBytes))
	}

	fileInfo := &storage.FileInfo{
		Key:         key,
		Size:        resp.ContentLength,
		ContentType: resp.Header.Get("Content-Type"),
	}
	lastModified := resp.Header.Get("Last-Modified")
	if lastModified != "" {
		tm, err := time.Parse(http.TimeFormat, lastModified)
		if err == nil {
			fileInfo.UpdatedAt = tm
		}
	}

	return resp.Body, fileInfo, nil
}

func (s *SupabaseStorage) Delete(ctx context.Context, key string) error {
	deleteURL := fmt.Sprintf("%s/storage/v1/object/%s/%s", s.projectURL, s.bucketName, key)
	payload := map[string][]string{"prefixes": {key}}
	payloadBytes, _ := json.Marshal(payload)

	req, err := http.NewRequestWithContext(ctx, "DELETE", deleteURL, bytes.NewReader(payloadBytes))
	if err != nil {
		return fmt.Errorf("failed to create delete request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+s.apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := s.client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to execute delete request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("delete failed with status %d: %s", resp.StatusCode, string(bodyBytes))
	}
	log.Printf("[SupabaseStorage] Delete successful for key: %s", key)
	return nil
}

func (s *SupabaseStorage) GetInfo(ctx context.Context, key string) (*storage.FileInfo, error) {
	log.Printf("[SupabaseStorage] GetInfo called for %s (using placeholder logic)", key)
	return nil, fmt.Errorf("GetInfo not fully implemented for SupabaseStorage")
}

func (s *SupabaseStorage) ListFiles(ctx context.Context) ([]storage.FileInfo, error) {
	log.Printf("[SupabaseStorage] ListFiles called (using placeholder logic)")
	return nil, fmt.Errorf("ListFiles not fully implemented for SupabaseStorage")
}

var _ storage.StorageService = (*SupabaseStorage)(nil)

func main() {
	ctx := context.Background()
	cfg := config.GetConfig()

	log.Printf("Running in %s mode", cfg.Environment)
	log.Printf("Using FundaVault URL: %s", cfg.FundaVaultURL)

	dbConfig := db.Config{
		ConnectionURL: os.Getenv("DATABASE_URL"),
	}
	database, err := db.NewConnection(dbConfig)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer database.Close()
	log.Println("Successfully connected to database")

	store := db.NewContentStore(database)

	storageInstance := NewSupabaseStorage(
		os.Getenv("SUPABASE_URL"),
		os.Getenv("SUPABASE_KEY"),
		"content",
	)
	log.Printf("[Debug] Initialized storage with URL: %s", os.Getenv("SUPABASE_URL"))

	firebaseService, err := firebase_admin.NewFirebaseAdminService(ctx)
	if err != nil {
		log.Fatalf("Failed to initialize Firebase Admin SDK: %v", err)
	}

	fundaVault := auth.NewFundaVaultClient(cfg)
	authMiddleware := middleware.NewAuthMiddleware(fundaVault)
	firebaseHandler := api.NewFirebaseHandler(firebaseService)

	downloadHandler := api.NewDownloadHandler(store, storageInstance)

	http.HandleFunc("/api/downloads/start",
		authMiddleware.AuthenticateDevice(downloadHandler.StartDownload))
	http.HandleFunc("/api/downloads/status",
		authMiddleware.AuthenticateDevice(downloadHandler.UpdateStatus))
	http.HandleFunc("/api/downloads/history",
		authMiddleware.AuthenticateDevice(downloadHandler.GetHistory))
	http.HandleFunc("/api/downloads/url",
		authMiddleware.AuthenticateDevice(downloadHandler.GetDownloadURL))

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

		fileInfo, err := storageInstance.Upload(r.Context(), file, header.Filename, header.Header.Get("Content-Type"))
		if err != nil {
			log.Printf("[Error] Upload failed: %v", err)
			http.Error(w, "Upload failed", http.StatusInternalServerError)
			return
		}

		log.Printf("[Success] File uploaded: %s", fileInfo.Key)

		contentTypeFromHeader := header.Header.Get("Content-Type")
		if err := store.Create(r.Context(), &db.Content{
			Name:        header.Filename,
			Type:        "linux-app",
			Version:     r.FormValue("version"),
			Description: r.FormValue("description"),
			AppVersion:  r.FormValue("app_version"),
			AppType:     r.FormValue("app_type"),
			FilePath:    fileInfo.Key,
			Size:        int(header.Size),
			StorageKey:  sql.NullString{String: fileInfo.Key, Valid: true},
			ContentType: sql.NullString{String: contentTypeFromHeader, Valid: contentTypeFromHeader != ""},
		}); err != nil {
			log.Printf("[Error] Database insert failed: %v", err)
			storageInstance.Delete(r.Context(), fileInfo.Key)
			http.Error(w, "Failed to create content record", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{
			"message": "File uploaded successfully",
			"key":     fileInfo.Key,
		})
	})

	http.HandleFunc("/download", func(w http.ResponseWriter, r *http.Request) {
		key := r.URL.Query().Get("key")
		if key == "" {
			http.Error(w, "Missing file key", http.StatusBadRequest)
			return
		}
		log.Printf("[Debug] Attempting to download file (deprecated): %s", key)
		reader, info, err := storageInstance.Download(r.Context(), key)
		if err != nil {
			log.Printf("[Error] Deprecated Download failed: %v", err)
			http.Error(w, "Download failed", http.StatusInternalServerError)
			return
		}
		defer reader.Close()
		w.Header().Set("Content-Type", info.ContentType)
		w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=\"%s\"", path.Base(key)))
		if info.Size > 0 {
			w.Header().Set("Content-Length", fmt.Sprintf("%d", info.Size))
		}
		if _, err := io.Copy(w, reader); err != nil {
			log.Printf("[Error] Streaming file failed (deprecated route): %v", err)
		}
	})

	http.HandleFunc("/api/content/list", func(w http.ResponseWriter, r *http.Request) {
		contents, err := store.List(r.Context())
		if err != nil {
			log.Printf("[Error] Failed to list content (deprecated route): %v", err)
			http.Error(w, "Failed to list content", http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(contents)
	})

	http.HandleFunc("/api/secure/firestore-write",
		authMiddleware.AuthenticateDevice(firebaseHandler.HandleSecureFirestoreWrite))

	http.HandleFunc("/download/", downloadHandler.HandleSignedDownload)

	log.Printf("Server starting on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
