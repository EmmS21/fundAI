# Book Embeddings Module

This module handles the generation, storage, and management of vector embeddings for PDF books using Nomic's embedding model.

## Overview

The Book Embeddings module is a critical component of the offline AI learning system. It processes PDF books to create semantic vector embeddings that enable:
- Intelligent search capabilities
- Content understanding
- Contextual question answering
- Study recommendations

## Components

### 1. Embedder (`embedder.py`)
The core embedding generation system that:
- Processes PDF books into structured text
- Generates hierarchical embeddings (chapter and chunk level)
- Handles compression and storage of embeddings
- Integrates with Google Drive for file access

**Key Features:**
- Hierarchical chunking with configurable overlap
- Chapter-level structure preservation
- Efficient compression of embedding vectors
- Google Drive integration for file access

### 2. Compression (`compression.py`)
Handles efficient storage and retrieval of embedding vectors:
- Compresses embedding vectors using zlib
- Maintains organized file structure
- Provides decompression utilities
- Optimizes storage space while maintaining quick access

### 3. Drive Storage (`drive_storage.py`)
Manages Google Drive operations for embedding storage:
- Creates and maintains embedding folder structure
- Handles file uploads and permissions
- Provides secure access to stored embeddings
- Manages temporary storage during processing

### 4. Orchestrator (`embedding_orchestrator.py`)
Coordinates the embedding generation process:
- Runs on Modal for scalable compute
- Monitors Firebase for books needing embeddings
- Manages the end-to-end embedding pipeline
- Updates book status in Firebase

## Usage

### Basic Usage
```python
from book_embeddings.embedder import BookEmbedder

embedder = BookEmbedder()
embedder.process_drive_book(file_id="your_file_id", output_dir="embeddings")
```

### Orchestrated Processing
```python
python -m book_embeddings.embedding_orchestrator
```

## Configuration

The module requires several environment variables:
- `NOMIC_API_KEY`: For accessing the embedding model
- `FIREBASE_*`: Firebase credentials for book management
- `GOOGLE_*`: Google Drive API credentials

## File Structure
```
book_embeddings/
├── __init__.py
├── embedder.py        # Core embedding generation
├── compression.py     # Embedding compression utilities
├── drive_storage.py   # Google Drive management
└── embedding_orchestrator.py  # Process orchestration
```

## Error Handling

The module includes comprehensive error handling for:
- PDF processing errors
- API failures (Nomic, Google Drive)
- Storage issues
- Network problems

Each component logs errors and updates Firebase with failure status when necessary.

## Dependencies

- `nomic`: Vector embedding generation
- `PyPDF2`: PDF processing
- `google-auth`: Google Drive authentication
- `firebase-admin`: Firebase integration
- `modal`: Compute orchestration
- `numpy`: Numerical operations
