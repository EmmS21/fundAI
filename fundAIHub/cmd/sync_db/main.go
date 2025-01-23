package main

import (
	"FundAIHub/internal/db"
	"FundAIHub/internal/storage"
	"context"
	"log"
	"os"
	"path"

	"github.com/joho/godotenv"
)

func main() {
	if err := godotenv.Load(); err != nil {
		log.Fatal("Error loading .env file")
	}

	// Initialize database connection
	dbConfig := db.Config{
		ConnectionURL: os.Getenv("DATABASE_URL"),
	}
	database, err := db.NewConnection(dbConfig)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer database.Close()

	store := db.NewContentStore(database)

	// Initialize Supabase storage
	storage := storage.NewSupabaseStorage(
		os.Getenv("SUPABASE_URL"),
		os.Getenv("SUPABASE_KEY"),
		"content",
	)

	// List all files in storage
	files, err := storage.ListFiles(context.Background())
	if err != nil {
		log.Fatalf("Failed to list files: %v", err)
	}

	// For each file, create a database record if it doesn't exist
	for _, file := range files {
		info, err := storage.GetInfo(context.Background(), file.Key)
		if err != nil {
			log.Printf("Failed to get info for %s: %v", file.Key, err)
			continue
		}

		// Check if record already exists
		exists, err := store.Exists(context.Background(), file.Key)
		if err != nil {
			log.Printf("Failed to check existence for %s: %v", file.Key, err)
			continue
		}

		if exists {
			log.Printf("Record already exists for %s, skipping", file.Key)
			continue
		}

		content := &db.Content{
			Name:        path.Base(file.Key),
			FilePath:    file.Key,
			Size:        int(info.Size),
			StorageKey:  file.Key,
			ContentType: info.ContentType,
		}

		if err := store.Create(context.Background(), content); err != nil {
			log.Printf("Failed to create record for %s: %v", file.Key, err)
			continue
		}

		log.Printf("Created record for %s", file.Key)
	}
}
