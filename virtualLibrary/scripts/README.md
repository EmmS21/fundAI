# Scripts Module

This module contains utility and maintenance scripts for managing the offline AI learning system's operational tasks.

## Overview

The Scripts module provides standalone utilities that handle system maintenance, updates, and one-off operations. These scripts support the core functionality of the system but are not part of the main application flow.

## Components

### 1. Embedding Access Manager (`update_embedding_access.py`)
Manages public access to embedding files and updates their status:

**Key Features:**
- Makes embedding folders publicly accessible
- Updates embedding status in Firebase
- Handles batch processing of books
- Manages Drive permissions

## Script Details

### Update Embedding Access Script

```python
from scripts.update_embedding_access import EmbeddingAccessManager
manager = EmbeddingAccessManager()
manager.update_embedded_books()
```


**Purpose:**
- Makes existing embedding folders publicly accessible
- Updates Firebase records to mark books as properly embedded
- Ensures all embedding files are readable by the offline AI system

**Process Flow:**
1. Queries Firebase for books with:
   - `embedding_status: "completed"`
   - `is_embedded: false`
2. For each book:
   - Extracts folder ID from embedding link
   - Makes folder publicly accessible
   - Makes all contained files accessible
   - Updates Firebase status

## File Structure
scripts/
├── __init__.py
├── update_embedding_access.py # Core embedding access management


## Usage

### Running Scripts

```bash
python -m scripts.update_embedding_access
```


### Expected Output
Made metadata.json publicly accessible
Made chapter_embedding.bin publicly accessible
Made texts.json publicly accessible
Made chunk_0.bin publicly accessible
...
Successfully updated access for book: [Book Title]


## Configuration

Requires access to:
- Firebase credentials
- Google Drive API credentials
- Proper scopes for Drive access

### Required Environment Variables
All credentials are accessed through the Config class:
- Firebase credentials
- Google Drive API credentials
- Service account details

## Error Handling

Comprehensive error handling for:
- Drive API permission errors
- Firebase operation failures
- Missing or invalid credentials
- Network connectivity issues

Each operation includes detailed logging and appropriate error messages.

## Dependencies

- `firebase-admin`: Firebase operations
- `google-auth`: Authentication
- `google-api-python-client`: Drive API access
- `datetime`: Timestamp management

## Security Notes

- Uses service account authentication
- Requires full Drive access scope
- Makes embedding folders publicly accessible (read-only)
- Updates are tracked with timestamps