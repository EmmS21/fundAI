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



# Integration Testing & Microservice Architecture
## System Architecture
FundAIHub works as a microservice architecture. The client is authenticated through FundaVault, the resultant JWT is decoded in FundAIHub to ascertain the user's subscription status and role. This determines the level of access the user has to the content in the FundAIHub store.

FundAI Platform:
1. FundaVault (Authentication Service)
   - User/Device Management
   - Subscription Tracking
   - Token Generation/Validation
   - Running on: Render (Python/FastAPI)

2. FundAIHub (Content Distribution)
   - App Store Management
   - Download Control
   - Content Versioning
   - Running on: Render (Go)

3. Storage Layer
   - Supabase: App content storage
   - PostgreSQL: User/content metadata

## Integration Points
### 1. Authentication Flow
Device → FundaVault (Token) → FundAIHub (Content)

Token Verification:
1. Device requests content from FundAIHub
2. FundAIHub verifies token with FundaVault
3. FundaVault validates device/subscription
4. FundAIHub serves/denies content

### 2. Testing Strategy
#### Local Testing Environment
```bash
# 1. Start FundaVault
cd fundaVault
uvicorn app.main:app --reload --port 8000

# 2. Start FundAIHub
cd fundAIHub
go run cmd/main.go
```

### Test Scenarios
#### 1. Public Access (No Auth)
```bash
# List available content
curl -X GET "http://localhost:8080/api/content/list" \
  -H "Content-Type: application/json"
```

#### 2. Subscribed User Flow
```bash
# 1. Register device with FundaVault
curl -X POST "http://localhost:8000/api/v1/devices/register/1" \
  -H "Content-Type: application/json"

# 2. Use returned token for downloads
curl -X POST "http://localhost:8080/api/downloads/start" \
  -H "Authorization: Bearer <token>" \
  -H "Device-ID: <device-id>" \
  -d '{"content_id": "<content-id>"}'
```

#### 3. Admin Operations
```bash
# 1. Get admin token from FundaVault
curl -X POST "http://localhost:8000/api/v1/admin/login" \
  -d '{
    "email": "admin@fundavault.com",
    "password": "your-password"
  }'

# 2. Use admin token for management
curl -X POST "http://localhost:8080/upload" \
  -H "Authorization: Bearer <admin-token>" \
  -F "file=@app.zip"
```

## Architecture Purpose
This microservice architecture serves several key purposes for the FundAI platform:

1. Offline Capability
- Tokens contain subscription data
- Local validation possible
- Reduced server dependency

2. Security Isolation
- Authentication separate from content
- Isolated failure domains

3. Educational Access
- Simplified device management
- Subscription tracking
- Content distribution control