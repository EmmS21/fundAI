# Virtual Library AI System

A comprehensive offline AI learning system designed to help students prepare for exams and learn new skills through AI-powered book interactions.

## Overview

This system manages a collection of educational books, processes them for AI interaction, and makes them available for offline use on student laptops. It handles:

- Book discovery and metadata management
- Vector embedding generation for AI understanding
- Synchronization between cloud services
- Access management for offline use

## Core Modules

### 1. Book Embeddings (`book_embeddings/`)
Generates and manages vector embeddings for books:
- Processes PDF books into semantic chunks
- Creates hierarchical embeddings using Nomic Embed v1.5
- Handles compression and storage optimization
- Manages Google Drive integration

### 2. Firebase Management (`firebase/`)
Central database management system:
- Tracks book metadata and status
- Manages embedding generation status
- Provides consistent database operations
- Handles authentication and access control

### 3. Google Drive Integration (`queryGoogleDrive/`)
Manages book discovery and ingestion:
- Scans designated Drive folders
- Extracts metadata from filenames
- Handles OAuth authentication
- Provides standardized book processing

### 4. Synchronization (`syncing_files/`)
Automated synchronization orchestration:
- Runs periodic checks for new books
- Updates metadata for existing books
- Manages cloud-based execution via Modal
- Ensures system consistency

### 5. Maintenance Scripts (`scripts/`)
Utility scripts for system maintenance:
- Updates embedding access permissions
- Manages batch operations
- Handles system updates
- Provides maintenance tools

## Setup

### Prerequisites
- Python 3.10+
- Google Cloud project with Drive API enabled
- Firebase project
- Nomic API access
- Modal account (for cloud execution)

### Environment Variables
Create a `.env` file with:

# Google Configuration
GOOGLE_CLIENT_ID="your_client_id"
GOOGLE_PROJECT_ID="your_project_id"
GOOGLE_CLIENT_SECRET="your_client_secret"
GOOGLE_AUTH_URI="https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI="https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_FOLDER_ID="your_folder_id"

# Firebase Configuration
FIREBASE_PROJECT_ID="your_firebase_project"
FIREBASE_PRIVATE_KEY="your_private_key"
FIREBASE_CLIENT_EMAIL="your_client_email"

# Nomic Configuration
NOMIC_API_KEY="your_nomic_key"

### Installation
```bash
Clone repository
git clone https://github.com/yourusername/virtualLibrary.git
cd virtualLibrary
pip install -r requirements.txt
```


## Usage

### Book Processing
1. Add books to designated Google Drive folder
2. Automatic synchronization will:
   - Detect new books
   - Generate embeddings
   - Update Firebase records
   - Make embeddings accessible

### Maintenance

```bash
# Update embedding access
python -m scripts.update_embedding_access
# Run manual sync
python -m syncing_files.orchestrator
```


## Architecture
virtualLibrary/
├── book_embeddings/ # Embedding generation and management
├── firebase/ # Database operations
├── queryGoogleDrive/ # Drive integration
├── scripts/ # Maintenance utilities
├── syncing_files/ # Synchronization orchestration
└── config.py # Configuration management


## Error Handling

Each module includes comprehensive error handling for:
- API failures
- Network issues
- Authentication problems
- Data processing errors

Errors are logged with detailed messages for debugging.

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request


## Contact

Emmanuel Sibanda - emmanuel@emmanuelsibanda.com
Project Link: https://github.com/EmmS21/virtualLibrary