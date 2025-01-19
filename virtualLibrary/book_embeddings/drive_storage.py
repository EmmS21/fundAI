"""
drive_storage.py

Purpose: Manage Google Drive storage operations for embeddings
Requires: Google Drive API credentials and folder management
"""

from google.oauth2 import service_account
from pathlib import Path
import tempfile
import os
from typing import Optional
from googleapiclient.discovery import build
from config import Config


class DriveEmbeddingStorage:
    def __init__(self):
        """Initialize Drive storage manager"""
        self.drive_service = self._initialize_drive_service()
        self.embeddings_folder_id = self._ensure_embeddings_folder()

    def get_temp_path(self, book_title: str) -> Path:
        """
        Get storage path for embeddings
        
        Args:
            book_title: Title of the book for naming the directory
            
        Returns:
            Path object pointing to the embeddings directory
        """
        try:
            base_dir = Path("embeddings")
            base_dir.mkdir(exist_ok=True)
            print(f"Created/verified base directory: {base_dir}")
            safe_title = "".join(c for c in book_title if c.isalnum() or c in (' ', '-', '_')).strip()
            book_dir = base_dir / f"{safe_title}_embeddings"
            book_dir.mkdir(exist_ok=True)
            print(f"Created/verified book directory: {book_dir}")   
            return book_dir
        except Exception as e:
            raise Exception(f"Failed to create embedding directory for {book_title}: {str(e)}")
        
    def _initialize_drive_service(self):
        """Initialize Google Drive service using service account"""
        # Create credentials from service account info
        credentials = service_account.Credentials.from_service_account_info({
            "type": "service_account",
            "project_id": Config.FIREBASE_PROJECT_ID,
            "private_key": Config.FIREBASE_PRIVATE_KEY,
            "client_email": Config.FIREBASE_CLIENT_EMAIL,
            "token_uri": "https://oauth2.googleapis.com/token",
        }, scopes=['https://www.googleapis.com/auth/drive.file'])
        
        return build('drive', 'v3', credentials=credentials)
        
    def _ensure_embeddings_folder(self) -> str:
        """Create or get embeddings folder ID"""
        try:
            # Check if embeddings folder exists
            query = "name='embeddings' and mimeType='application/vnd.google-apps.folder'"
            results = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            existing = results.get('files', [])
            if existing:
                return existing[0]['id']
                
            # Create if doesn't exist
            file_metadata = {
                'name': 'embeddings',
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            file = self.drive_service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            return file.get('id')
            
        except Exception as e:
            raise Exception(f"Failed to ensure embeddings folder: {str(e)}")
            
    def get_temp_path(self, book_title: str) -> Path:
        """Get temporary storage path for embeddings"""
        temp_dir = Path(tempfile.mkdtemp())
        return temp_dir / f"{book_title}_embeddings"
        
    def store_embedding(self, 
                       embedding_path: Path, 
                       book_title: str) -> str:
        """
        Store embeddings in Drive and return link
        
        Args:
            embedding_path: Path to embedding files
            book_title: Original book title for naming
            
        Returns:
            Google Drive link to embedding folder
        """
        try:
            # Create book-specific embedding folder
            folder_metadata = {
                'name': f"{book_title}_embeddings",
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self.embeddings_folder_id]
            }
            
            folder = self.drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            
            # Upload all embedding files
            for file_path in embedding_path.rglob('*'):
                if file_path.is_file():
                    file_metadata = {
                        'name': file_path.name,
                        'parents': [folder_id]
                    }
                    
                    # Upload file
                    self.drive_service.files().create(
                        body=file_metadata,
                        media_body=str(file_path),
                        fields='id'
                    ).execute()
            
            return f"https://drive.google.com/drive/folders/{folder_id}"
            
        except Exception as e:
            raise Exception(f"Failed to store embeddings: {str(e)}")
