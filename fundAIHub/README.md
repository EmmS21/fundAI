# FundAIHub - Content Distribution System
FundAIHub is a store for linux native applications. These are EdTech applications interfacing with local AI models as a part of a broader build to give students in Africa access to laptops preloaded with offline AI models.

Students will be able to download different tools from this store. Downloads will go through a middleware checking if the user is subscribed based on their devide ID.

The apps are stored in supabase.

## Core Features
- Content upload and versioning
- Secure download management
- Version comparison and updates
- Download status tracking
- Device-specific content distribution

## Testing Guide

### Prerequisites
- Go 1.20+
- PostgreSQL database
- Environment variables configured

### Environment Setup

```bash
# Required environment variables
export DATABASE_URL="postgresql://user:password@localhost:5432/fundaihub"
```

### Running Tests

```bash
# Run all tests
go test ./...

# Run specific test suites
go test -v ./internal/api -run TestDownloadStatusUpdates
go test -v ./internal/api -run TestDownloadFlow
# Test URL Generation and Validation
go test -v ./internal/api -run TestURLGenerator
```

## Test Suites
### 1. Download Status Management (TestDownloadStatusUpdates)
Tests the download status lifecycle management.

```bash
go test -v ./internal/api -run TestDownloadStatusUpdates
```

#### Tests:
- Status transition from "started" to "completed"
- Status transition from "started" to "paused"
- Bytes downloaded tracking
- Error message handling

**Expected Responses:**
```json
{
    "id": "uuid",
    "status": "completed",
    "bytes_downloaded": 1024,
    "error_message": null
}
```

### 2. Download Flow (TestDownloadFlow)
Tests the complete download process including authentication.

```bash
go test -v ./internal/api -run TestDownloadFlow
```

#### Tests:
- Download initiation
- Device authentication
- User authorization
- Content validation

### 3. URL Generation and Validation (TestURLGenerator)
Tests the secure download URL generation and validation system.

```bash
go test -v ./internal/api -run TestURLGenerator
```

#### Tests:
- Generate secure, time-limited download URLs
- Validate URL signatures
- Handle URL expiration
- Prevent URL tampering
- Content existence verification

**Expected Responses:**
```json
{
    "download_url": "/download/content-uuid?expires=2024-01-23T20:00:00Z&signature=abc123...",
    "expires_in": "1h"
}
```

## API Endpoints
### Content Upload

```bash
curl -X POST http://localhost:8080/upload \
  -F "file=@sample.pdf" \
  -F "version=1.0.0" \
  -F "description=Linux text editor" \
  -F "app_version=2.1.0" \
  -F "app_type=editor"
```

**Expected Response:**

```json
{
    "id": "uuid",
    "name": "sample.pdf",
    "version": "1.0.0",
    "size": 1024,
    "content_type": "application/pdf"
}
```

### Start Download

```bash
curl -X POST http://localhost:8080/api/downloads/start \
  -H "Content-Type: application/json" \
  -H "Device-ID: device_uuid" \
  -d '{"content_id": "content_uuid"}'
```

### Update Download Status

```bash
curl -X PUT http://localhost:8080/api/downloads/status?id=download_uuid \
  -H "Content-Type: application/json" \
  -H "Device-ID: device_uuid" \
  -d '{"status": "completed", "bytes_downloaded": 1024}'
```

### Get Download History

```bash
curl -X GET http://localhost:8080/api/downloads/history \
  -H "Device-ID: device_uuid"
```

## Test Behaviors
### Authentication & Authorization
- Validates device ID in requests
- Verifies user permissions
- Handles invalid authentication

### Content Management
- Validates upload parameters
- Handles file storage
- Manages content version

### Download Management
- Tracks download progress
- Handles pause/resume
- Updates status correctly
- Records download history

### Error Handling
- Invalid content IDs
- Missing parameters
- Database errors
- Authentication failures

