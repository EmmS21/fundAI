package main

import (
	"log"
	"net/http"
	"os"

	"FundAIHub/internal/api"
	"FundAIHub/internal/db"

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

	// Initialize handlers
	contentHandler := api.NewContentHandler(contentStore)

	// Setup routes
	http.HandleFunc("/api/content", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			contentHandler.List(w, r)
		case http.MethodPost:
			contentHandler.Create(w, r)
		case http.MethodPut:
			contentHandler.Update(w, r)
		case http.MethodDelete:
			contentHandler.Delete(w, r)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	// Start server
	log.Println("Server starting on :8080")
	if err := http.ListenAndServe(":8080", nil); err != nil {
		log.Fatal(err)
	}
}
