package db

import (
	"context"
	"database/sql"
	"log"

	"github.com/google/uuid"
	_ "github.com/lib/pq"
)

// Config simplified to just use connection string
type Config struct {
	ConnectionURL string
}

func NewConnection(cfg Config) (*sql.DB, error) {
	log.Printf("Attempting to connect to database with URL: %s", cfg.ConnectionURL)
	db, err := sql.Open("postgres", cfg.ConnectionURL)
	if err != nil {
		log.Printf("Error opening database: %v", err)
		return nil, err
	}

	// Test the connection
	err = db.Ping()
	if err != nil {
		log.Printf("Error pinging database: %v", err)
		return nil, err
	}

	log.Println("Successfully connected to database")
	return db, nil
}

// ContentStore handles database operations for content
type ContentStore struct {
	db *sql.DB
}

// NewContentStore creates a new ContentStore
func NewContentStore(db *sql.DB) *ContentStore {
	return &ContentStore{db: db}
}

// List returns all content from the database
func (s *ContentStore) List(ctx context.Context) ([]Content, error) {
	query := `SELECT id, name, type, version, file_path, size, created_at, updated_at FROM content`

	rows, err := s.db.QueryContext(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var contents []Content
	for rows.Next() {
		var c Content
		err := rows.Scan(&c.ID, &c.Name, &c.Type, &c.Version, &c.FilePath, &c.Size, &c.CreatedAt, &c.UpdatedAt)
		if err != nil {
			return nil, err
		}
		contents = append(contents, c)
	}
	return contents, nil
}

// Create adds a new content record
func (s *ContentStore) Create(ctx context.Context, content *Content) error {
	query := `
		INSERT INTO content (name, type, version, file_path, size, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
        RETURNING id, created_at, updated_at`

	return s.db.QueryRowContext(
		ctx,
		query,
		content.Name,
		content.Type,
		content.Version,
		content.FilePath,
		content.Size,
	).Scan(&content.ID, &content.CreatedAt, &content.UpdatedAt)
}

// Update modifies an existing content record
func (s *ContentStore) Update(ctx context.Context, content *Content) error {
	query := `
		UPDATE content 
		SET name = $1, type = $2, version = $3, file_path = $4, size = $5, updated_at = NOW()
		WHERE id = $6`

	result, err := s.db.ExecContext(
		ctx,
		query,
		content.Name,
		content.Type,
		content.Version,
		content.FilePath,
		content.Size,
		content.ID,
	)
	if err != nil {
		return err
	}

	rows, err := result.RowsAffected()
	if err != nil {
		return err
	}
	if rows == 0 {
		return sql.ErrNoRows
	}
	return nil
}

// Delete removes a content record
func (s *ContentStore) Delete(ctx context.Context, id uuid.UUID) error {
	query := `DELETE FROM content WHERE id = $1`

	result, err := s.db.ExecContext(ctx, query, id)
	if err != nil {
		return err
	}

	rows, err := result.RowsAffected()
	if err != nil {
		return err
	}
	if rows == 0 {
		return sql.ErrNoRows
	}
	return nil
}
