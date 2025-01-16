"""
Book Embedding Processor

Purpose: Process PDF books and generate vector embeddings using Nomic Embed v1.5
with hierarchical chunking and structure preservation.
"""

import PyPDF2
import json
import numpy as np
from pathlib import Path
import re
from typing import Dict, List, Tuple
from nomic import embed
import zlib
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaIoBaseDownload
import io
import tempfile
import os
import pickle

class BookEmbedder:
    def __init__(self, 
                 chunk_size: int = 512,
                 chunk_overlap: int = 50,
                 model: str = "nomic-embed-text-v1.5",
                 dimensionality: int = 768):
        """
        Initialize the book embedder with configurable parameters.
        
        Args:
            chunk_size: Target size for text chunks (in tokens)
            chunk_overlap: Overlap between chunks to maintain context
            model: Nomic embedding model to use
            dimensionality: Output embedding dimension (for v1.5)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.model = model
        self.dimensionality = dimensionality
        self.drive_service = self._initialize_drive_service()

    def _initialize_drive_service(self):
        """Initialize Google Drive service with proper authentication"""
        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        creds = None
        token_path = Path(__file__).parent / 'token.pickle'
        
        if token_path.exists():
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
                
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(Path(__file__).parent.parent / 'queryGoogleDrive' / 'googleOAuth.json'), 
                    SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        return build('drive', 'v3', credentials=creds)

    def extract_text_with_structure(self, pdf_path: str) -> Dict[str, str]:
        """
        Extract text from PDF while preserving chapter structure.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary mapping chapter titles to their content
        """
        chapters = {}
        current_chapter = "Introduction"
        current_text = []
        
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            for page in reader.pages:
                text = page.extract_text()
                
                # Simple chapter detection (can be enhanced)
                chapter_match = re.match(r'^Chapter\s+\d+[:\s]+(.*?)$', text, re.MULTILINE)
                if chapter_match:
                    # Save previous chapter
                    if current_text:
                        chapters[current_chapter] = '\n'.join(current_text)
                    current_chapter = chapter_match.group(1)
                    current_text = []
                
                current_text.append(text)
        
        # Save final chapter
        if current_text:
            chapters[current_chapter] = '\n'.join(current_text)
            
        return chapters

    def create_chunks(self, text: str) -> List[str]:
        """
        Create overlapping chunks from text.
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of text chunks
        """
        chunks = []
        sentences = text.split('. ')
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence.split())
            if current_size + sentence_size > self.chunk_size:
                # Save current chunk
                chunks.append('. '.join(current_chunk) + '.')
                # Keep overlap sentences
                overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                current_chunk = current_chunk[overlap_start:]
                current_size = sum(len(s.split()) for s in current_chunk)
            
            current_chunk.append(sentence)
            current_size += sentence_size
        
        if current_chunk:
            chunks.append('. '.join(current_chunk) + '.')
            
        return chunks

    def embed_text(self, texts: List[str], task_type: str) -> np.ndarray:
        """
        Generate embeddings using Nomic Embed.
        
        Args:
            texts: List of text chunks to embed
            task_type: Embedding task type ('search_document', 'search_query', etc.)
            
        Returns:
            Array of embeddings
        """
        response = embed.text(
            texts=texts,
            model=self.model,
            task_type=task_type,
            dimensionality=self.dimensionality
        )
        return np.array(response['embeddings'])

    def process_book(self, pdf_path: str, output_dir: str):
        """
        Process a book and generate hierarchical embeddings.
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Directory to save embeddings
        """
        # Extract text with structure
        chapters = self.extract_text_with_structure(pdf_path)
        
        # Create output structure
        book_name = Path(pdf_path).stem
        output_path = Path(output_dir) / book_name
        output_path.mkdir(parents=True, exist_ok=True)
        
        embeddings_data = {
            'metadata': {
                'book_name': book_name,
                'model': self.model,
                'dimensionality': self.dimensionality,
                'chunk_size': self.chunk_size,
                'chunk_overlap': self.chunk_overlap
            },
            'chapters': {}
        }

        # Process each chapter
        for chapter_title, chapter_text in chapters.items():
            # Create chapter-level embedding
            chapter_embedding = self.embed_text([chapter_text], 'search_document')[0]
            
            # Create chunk-level embeddings
            chunks = self.create_chunks(chapter_text)
            chunk_embeddings = self.embed_text(chunks, 'search_document')
            
            embeddings_data['chapters'][chapter_title] = {
                'chapter_embedding': self._compress_embedding(chapter_embedding),
                'chunks': {
                    'texts': chunks,
                    'embeddings': [self._compress_embedding(emb) for emb in chunk_embeddings]
                }
            }
        
        # Save embeddings
        self._save_embeddings(embeddings_data, output_path)

    def _compress_embedding(self, embedding: np.ndarray) -> bytes:
        """
        Compress embedding vector using zlib.
        
        Args:
            embedding: Numpy array embedding
            
        Returns:
            Compressed bytes
        """
        return zlib.compress(embedding.tobytes())

    def _save_embeddings(self, data: Dict, output_path: Path):
        """
        Save compressed embeddings and metadata.
        
        Args:
            data: Embeddings and metadata
            output_path: Output directory path
        """
        # Save metadata separately
        with open(output_path / 'metadata.json', 'w') as f:
            json.dump(data['metadata'], f, indent=2)
        
        # Save compressed embeddings
        for chapter, chapter_data in data['chapters'].items():
            chapter_path = output_path / 'chapters' / chapter
            chapter_path.mkdir(parents=True, exist_ok=True)
            
            # Save chapter embedding
            with open(chapter_path / 'chapter_embedding.bin', 'wb') as f:
                f.write(chapter_data['chapter_embedding'])
            
            # Save chunk data
            chunks_path = chapter_path / 'chunks'
            chunks_path.mkdir(exist_ok=True)
            
            # Save chunk texts
            with open(chunks_path / 'texts.json', 'w') as f:
                json.dump(chapter_data['chunks']['texts'], f, indent=2)
            
            # Save chunk embeddings
            for i, emb in enumerate(chapter_data['chunks']['embeddings']):
                with open(chunks_path / f'chunk_{i}.bin', 'wb') as f:
                    f.write(emb)

    def process_drive_book(self, file_id: str, output_dir: str):
        """
        Process a book directly from Google Drive
        
        Args:
            file_id: Google Drive file ID
            output_dir: Directory to save embeddings
        """
        try:
            # Download file
            request = self.drive_service.files().get_media(fileId=file_id)
            temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            
            downloader = MediaIoBaseDownload(temp_file, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(f"Download {int(status.progress() * 100)}%")
            
            temp_file.close()
            
            # Process using existing method
            self.process_book(temp_file.name, output_dir)
            
            # Cleanup
            os.unlink(temp_file.name)
            
        except Exception as e:
            raise Exception(f"Error processing Drive book: {str(e)}")

if __name__ == "__main__":
    embedder = BookEmbedder()
    file_id = "YOUR_DRIVE_FILE_ID"  # Replace with actual file ID
    output_dir = "test_embeddings"
    
    try:
        embedder.process_drive_book(file_id, output_dir)
        print(f"Successfully processed book. Embeddings saved to {output_dir}")
    except Exception as e:
        print(f"Error: {str(e)}") 