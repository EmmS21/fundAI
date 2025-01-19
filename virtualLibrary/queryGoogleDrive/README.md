# Query Google Drive Module

This module manages the discovery and synchronization of educational books from Google Drive, handling file scanning and metadata extraction.

## Overview

The Query Google Drive module serves as the initial data ingestion system for the offline AI learning platform. It:
- Scans designated Google Drive folders for educational materials
- Extracts structured metadata from filenames
- Manages OAuth authentication for Drive access
- Provides standardized book metadata for the system

## Components

### 1. Drive Scanner (`syncBook.py`)
Handles Google Drive interactions and file discovery:

**Key Features:**
- OAuth 2.0 authentication flow
- Automated token management
- Folder scanning
- File metadata retrieval

### 2. Metadata Parser (`metadata_parser.py`)
Extracts structured metadata from book filenames:

**Key Features:**
- Multiple filename pattern support
- Year extraction
- Author-title separation
- Standardized metadata output

## Supported Filename Patterns

The parser handles various filename formats:

Title - Author.pdf
Title_with_underscores - Author.pdf
Title (Year) - Author.pdf
Title - Author (Year).pdf
Title[Tag] (Year).pdf # For academic papers


## Metadata Structure

```json
{
'title': 'Book Title',
'author': 'Author Name',
'year': 'YYYY', # Optional
'drive_id': 'Google Drive File ID',
'drive_link': 'https://drive.google.com/file/d/...',
'created_time': 'timestamp',
'modified_time': 'timestamp',
'original_filename': 'original.pdf'
}
```


## Usage

### Basic Usage

```python
from queryGoogleDrive.syncBook import DriveScanner
from config import Config
Initialize scanner
scanner = DriveScanner(Config.GOOGLE_DRIVE_FOLDER_ID)
List and parse files
files = scanner.list_files()
for file in files:
metadata = scanner.parser.parse_drive_file(file)
print(f"Found book: {metadata['title']} by {metadata['author']}")
```

## Authentication

### OAuth Flow
1. Checks for existing token in `token.pickle`
2. If no token exists:
   - Initiates OAuth flow
   - Opens browser for user authentication
   - Saves token for future use
3. Handles token refresh automatically

### Required Credentials
- Google OAuth client configuration (`googleOAuth.json`)
- Drive API scopes: `https://www.googleapis.com/auth/drive.readonly`

## File Structure
queryGoogleDrive/
├── init.py
├── syncBook.py # Drive scanning and auth
├── metadata_parser.py # Filename parsing

## Error Handling

Comprehensive error handling for:
- Authentication failures
- Drive API errors
- Invalid filename patterns
- Metadata extraction errors

Each component includes detailed error messages and appropriate exception handling.

## Dependencies

- `google-auth-oauthlib`: OAuth authentication
- `google-api-python-client`: Drive API access
- `pickle`: Token storage
- `pathlib`: Path management