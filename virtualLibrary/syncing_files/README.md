# Syncing Files Module

This module manages automated synchronization between Google Drive and Firebase, ensuring the system's book catalog stays up-to-date.

## Overview

The Syncing Files module provides automated orchestration for keeping the offline AI learning system's book catalog synchronized. It:
- Runs periodic checks for new books
- Updates metadata for existing books
- Manages the synchronization between Google Drive and Firebase
- Runs on Modal for reliable cloud execution

## Components

### 1. Orchestrator (`orchestrator.py`)
Manages automated synchronization using Modal:

**Key Features:**
- Hourly automated synchronization
- Cloud-based execution
- Secure credential management
- Comprehensive error handling

## Synchronization Process

### Flow
1. Scans Google Drive folder for books
2. Compares with Firebase database
3. Processes changes:
   - Adds new books
   - Updates modified books
   - Maintains metadata consistency

### State Management

```python
{
'drive_id': {
'title': 'Book Title',
'author': 'Author Name',
'year': 'Publication Year',
'drive_link': 'https://drive.google.com/...',
'updated_date': 'timestamp',
'doc_id': 'firebase_doc_id'
}
}```


## Usage

### Local Development
```bash
python -m syncing_files.orchestrator
```


### Production Deployment

```python
# Runs every hour on schedule
modal deploy syncing_files.orchestrator
```


## Configuration

### Modal Setup
- App Name: "orchestrator"
- Schedule: Hourly
- Python Version: 3.10
- Base Image: debian_slim

### Required Secrets
```python
{
"GOOGLE_CLIENT_ID": "...",
"GOOGLE_CLIENT_SECRET": "...",
"FIREBASE_PRIVATE_KEY": "...",
"GOOGLE_DRIVE_FOLDER_ID": "...",
"FIREBASE_PROJECT_ID": "...",
"FIREBASE_CLIENT_EMAIL": "..."
}
```


## File Structure

syncing_files/
├── init.py
└── orchestrator.py # Modal-based sync orchestration


## Dependencies

### Python Packages
- `modal`: Cloud execution
- `google-auth-oauthlib`: Google authentication
- `firebase-admin`: Firebase operations
- `google-api-python-client`: Drive API
- Additional support packages:
  - `python-dotenv`
  - `google-cloud-firestore`
  - `google-cloud-storage`
  - `cachecontrol`
  - `google-api-core`
  - `pyjwt`

## Error Handling

Comprehensive error handling for:
- Drive scanning errors
- Firebase operation failures
- Metadata parsing issues
- Network connectivity problems
- Authentication failures

Each operation includes detailed logging and appropriate error messages.

## Monitoring

### Logs
- Successful additions: "Added new book: {title}"
- Updates: "Updated book: {title}"
- Parsing errors: "Error parsing file {name}: {error}"
- Sync status: "Synchronization completed successfully"
- Failures: "Synchronization failed: {error}"

## Security

- Runs in isolated Modal environment
- Uses secure secret management
- Implements proper authentication
- Maintains least-privilege access