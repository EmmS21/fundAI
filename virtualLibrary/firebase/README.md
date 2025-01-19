# Firebase Module

This module manages all Firebase interactions for the offline AI learning system, primarily handling book metadata and embedding status tracking.

## Overview

The Firebase module serves as the central database management system for the application. It:
- Tracks all books available in the system
- Manages embedding generation status
- Stores metadata about books and their embeddings
- Provides a consistent interface for database operations

## Components

### 1. Database Operations (`db_operations.py`)
Handles all Firebase Firestore interactions through the `FirebaseManager` class:

**Key Features:**
- Book metadata management
- Embedding status tracking
- Timestamp management
- Document querying and updates

### Book Document Structure

```json
{
"title": "Book Title",
"author": "Author Name",
"year": "Publication Year",
"drive_id": "Google Drive File ID",
"embedding_status": "completed|processing|failed",
"embedding_link": "Drive folder URL",
"is_embedded": boolean,
"added_date": timestamp,
"updated_date": timestamp,
"embedding_started_at": timestamp,
"embedding_completed_at": timestamp,
"embedding_error": "Error message if failed"
}
```

## Core Operations

### Book Management
- **Get Books**: Retrieve all books with metadata
- **Add Book**: Add new book with initial metadata
- **Update Book**: Modify existing book metadata
- **Find Book**: Query books by Drive ID

### Embedding Status Management
Tracks the full lifecycle of embedding generation:
- Initial state (`is_embedded: false`)
- Processing state (`embedding_status: "processing"`)
- Completion state (`embedding_status: "completed"`)
- Error handling (`embedding_status: "failed"`)

## Usage

### Basic Usage

```python
from firebase.db_operations import FirebaseManager
Initialize manager
firebase = FirebaseManager()
Get all books
books = firebase.get_existing_books()
Add new book
book_metadata = {
"title": "Example Book",
"author": "Author Name",
"drive_id": "drive_file_id"
}
```


## Configuration

Requires Firebase credentials in environment variables:
- `FIREBASE_PROJECT_ID`
- `FIREBASE_PRIVATE_KEY_ID`
- `FIREBASE_PRIVATE_KEY`
- `FIREBASE_CLIENT_EMAIL`
- `FIREBASE_CLIENT_ID`
- `FIREBASE_AUTH_URI`
- `FIREBASE_TOKEN_URI`
- `FIREBASE_AUTH_PROVIDER_CERT_URL`
- `FIREBASE_CLIENT_CERT_URL`

## File Structure
firebase/
├── init.py
└── db_operations.py # Core database operations


## Error Handling

Comprehensive error handling for:
- Firebase authentication failures
- Database operation errors
- Missing credentials
- Query failures

All operations include try-catch blocks with detailed error messages.

## Dependencies

- `firebase-admin`: Firebase SDK
- `google-auth`: Authentication
- `datetime`: Timestamp management