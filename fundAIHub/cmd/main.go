package main

import (
	"log"
	"net/http"
	"os"

	"FundAIHub/internal/api"
	"FundAIHub/internal/db"
	"FundAIHub/internal/storage"

	"github.com/joho/godotenv"
)

func main() {
	// Load .env file
	if err := godotenv.Load(); err != nil {
		log.Println("No .env file found")
	}

	// Get database URL from environment variable
	dbURL := os.Getenv("DATABASE_URL")
	if dbURL == "" {
		log.Fatal("DATABASE_URL environment variable is not set")
	}

	// Initialize database connection
	dbConfig := db.Config{
		ConnectionURL: dbURL,
	}

	dbConn, err := db.NewConnection(dbConfig)
	if err != nil {
		log.Fatal("Failed to connect to database:", err)
	}
	defer dbConn.Close()

	// Initialize stores
	contentStore := db.NewContentStore(dbConn)

	// Initialize storage service
	storageService := storage.NewSupabaseStorage(
		os.Getenv("SUPABASE_URL"),
		os.Getenv("SUPABASE_KEY"),
		"content", // bucket name
	)

	// Initialize handlers
	contentHandler := api.NewContentHandler(contentStore, storageService)

	// Before starting the server
	log.Printf("Starting server with storage URL: %s", os.Getenv("SUPABASE_URL"))
	log.Printf("Content bucket name: %s", "content")

	// Setup routes
	http.HandleFunc("/api/content", func(w http.ResponseWriter, r *http.Request) {
		log.Printf("Received %s request to /api/content", r.Method)
		log.Printf("Content-Type: %s", r.Header.Get("Content-Type"))

		switch r.Method {
		case http.MethodGet:
			contentHandler.List(w, r)
		case http.MethodPost:
			if r.Header.Get("Content-Type") == "multipart/form-data" {
				log.Println("Handling file upload")
				contentHandler.UploadFile(w, r)
			} else {
				contentHandler.Create(w, r)
			}
		case http.MethodPut:
			contentHandler.Update(w, r)
		case http.MethodDelete:
			contentHandler.Delete(w, r)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	// Add download endpoint
	http.HandleFunc("/api/content/download/", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		contentHandler.DownloadFile(w, r)
	})

	// Add health check endpoint
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		log.Println("Health check called")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	// Start server
	log.Println("Server starting on :8080")
	if err := http.ListenAndServe(":8080", nil); err != nil {
		log.Fatal(err)
	}
}
