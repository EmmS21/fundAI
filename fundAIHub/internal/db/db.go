package db

import (
	"context"
	"database/sql"
	"fmt"
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

// Get retrieves a content record by ID
func (s *ContentStore) Get(ctx context.Context, id uuid.UUID) (*Content, error) {
	query := `
		SELECT id, name, type, version, file_path, size, storage_key, content_type, created_at, updated_at 
		FROM content 
		WHERE id = $1`

	var content Content
	err := s.db.QueryRowContext(ctx, query, id).Scan(
		&content.ID,
		&content.Name,
		&content.Type,
		&content.Version,
		&content.FilePath,
		&content.Size,
		&content.StorageKey,
		&content.ContentType,
		&content.CreatedAt,
		&content.UpdatedAt,
	)
	if err != nil {
		return nil, err
	}
	return &content, nil
}

// Exists checks if a record exists for the given storage key
func (s *ContentStore) Exists(ctx context.Context, storageKey string) (bool, error) {
	var exists bool
	query := `SELECT EXISTS(SELECT 1 FROM content WHERE storage_key = $1)`
	err := s.db.QueryRowContext(ctx, query, storageKey).Scan(&exists)
	return exists, err
}

type DownloadStore interface {
	Create(ctx context.Context, download *Download) error
	Update(ctx context.Context, download *Download) error
	GetByID(ctx context.Context, id uuid.UUID) (*Download, error)
	ListDownloadsByDeviceID(ctx context.Context, deviceID uuid.UUID) ([]*Download, error)
}

// Add these methods to your ContentStore struct
func (s *ContentStore) CreateDownload(ctx context.Context, download *Download) error {
	query := `
        INSERT INTO downloads (device_id, user_id, content_id, status, bytes_downloaded, total_bytes)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, created_at`

	return s.db.QueryRowContext(
		ctx,
		query,
		download.DeviceID,
		download.UserID,
		download.ContentID,
		download.Status,
		download.BytesDownloaded,
		download.TotalBytes,
	).Scan(&download.ID, &download.StartedAt)
}

func (s *ContentStore) GetDownloadByID(ctx context.Context, id uuid.UUID) (*Download, error) {
	log.Printf("[Debug] Looking for download with ID: %s", id)

	query := `
        SELECT id, device_id, user_id, content_id, status, bytes_downloaded, 
               total_bytes, created_at, last_updated_at, completed_at, error_message, 
               resume_position
        FROM downloads 
        WHERE id = $1`

	download := &Download{}
	err := s.db.QueryRowContext(ctx, query, id).Scan(
		&download.ID,
		&download.DeviceID,
		&download.UserID,
		&download.ContentID,
		&download.Status,
		&download.BytesDownloaded,
		&download.TotalBytes,
		&download.StartedAt,
		&download.LastUpdatedAt,
		&download.CompletedAt,
		&download.ErrorMessage,
		&download.ResumePosition,
	)
	if err != nil {
		log.Printf("[Error] Database error: %v", err)
		return nil, err
	}
	log.Printf("[Debug] Found download in database: %+v", download)
	return download, nil
}

func (s *ContentStore) UpdateDownload(ctx context.Context, download *Download) error {
	query := `
		UPDATE downloads 
		SET status = $1, 
			bytes_downloaded = $2, 
        	error_message = COALESCE($3::text, error_message),
			last_updated_at = NOW(),
			completed_at = CASE 
				WHEN status = 'completed' 
				THEN NOW() 
				ELSE completed_at 
			END
		WHERE id = $4`

	var errorMsg interface{}
	if download.ErrorMessage != nil {
		errorMsg = *download.ErrorMessage
	} else {
		errorMsg = nil
	}

	result, err := s.db.ExecContext(
		ctx,
		query,
		download.Status,
		download.BytesDownloaded,
		errorMsg,
		download.ID,
	)
	if err != nil {
		return err
	}

	rows, err := result.RowsAffected()
	if err != nil {
		return err
	}
	if rows == 0 {
		return fmt.Errorf("download not found")
	}
	return nil
}

func (s *ContentStore) ListDownloadsByDeviceID(ctx context.Context, deviceID uuid.UUID) ([]*Download, error) {
	query := `
        SELECT id, device_id, user_id, content_id, status, bytes_downloaded, 
               total_bytes, created_at, last_updated_at, completed_at, error_message, 
               resume_position
        FROM downloads 
        WHERE device_id = $1
        ORDER BY created_at DESC`

	rows, err := s.db.QueryContext(ctx, query, deviceID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var downloads []*Download
	for rows.Next() {
		download := &Download{}
		err := rows.Scan(
			&download.ID,
			&download.DeviceID,
			&download.UserID,
			&download.ContentID,
			&download.Status,
			&download.BytesDownloaded,
			&download.TotalBytes,
			&download.StartedAt,
			&download.LastUpdatedAt,
			&download.CompletedAt,
			&download.ErrorMessage,
			&download.ResumePosition,
		)
		if err != nil {
			return nil, err
		}
		downloads = append(downloads, download)
	}
	return downloads, nil
}

func (s *ContentStore) GetByID(ctx context.Context, id uuid.UUID) (*Content, error) {
	query := `
		SELECT id, name, type, version, file_path, size
		FROM content
		WHERE id = $1`

	content := &Content{}
	err := s.db.QueryRowContext(ctx, query, id).Scan(
		&content.ID,
		&content.Name,
		&content.Type,
		&content.Version,
		&content.FilePath,
		&content.Size,
	)
	if err != nil {
		return nil, err
	}

	return content, nil
}
