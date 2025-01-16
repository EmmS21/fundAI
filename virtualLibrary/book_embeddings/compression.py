"""
Compression utilities for embedding storage

Purpose: Handle efficient compression and decompression of embeddings
using optimized algorithms and storage formats.
"""

import numpy as np
import zlib
from typing import Dict, Union, List
import json
from pathlib import Path

class EmbeddingCompressor:
    def __init__(self, compression_level: int = 6):
        """
        Initialize the compressor with configurable compression level.
        
        Args:
            compression_level: zlib compression level (1-9, higher = better compression but slower)
        """
        self.compression_level = compression_level

    def compress_embedding(self, embedding: np.ndarray) -> bytes:
        """
        Compress a single embedding vector.
        
        Args:
            embedding: Numpy array of embedding vectors
            
        Returns:
            Compressed bytes
        """
        return zlib.compress(embedding.tobytes(), level=self.compression_level)

    def decompress_embedding(self, compressed_data: bytes, shape: tuple) -> np.ndarray:
        """
        Decompress embedding data back to numpy array.
        
        Args:
            compressed_data: Compressed embedding bytes
            shape: Shape of the original embedding array
            
        Returns:
            Decompressed numpy array
        """
        decompressed = zlib.decompress(compressed_data)
        return np.frombuffer(decompressed).reshape(shape)

    def save_compressed_embeddings(self, 
                                 data: Dict, 
                                 output_path: Path,
                                 chunk_prefix: str = "chunk_"):
        """
        Save compressed embeddings and metadata with organized structure.
        
        Args:
            data: Dictionary containing embeddings and metadata
            output_path: Base path for saving files
            chunk_prefix: Prefix for chunk embedding files
        """
        # Save metadata separately
        with open(output_path / 'metadata.json', 'w') as f:
            json.dump(data['metadata'], f, indent=2)
        
        # Save compressed embeddings by chapter
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
                with open(chunks_path / f'{chunk_prefix}{i}.bin', 'wb') as f:
                    f.write(emb)

    def load_compressed_embeddings(self, 
                                 base_path: Path,
                                 dimensionality: int) -> Dict:
        """
        Load compressed embeddings and metadata.
        
        Args:
            base_path: Path to embedding directory
            dimensionality: Expected embedding dimension
            
        Returns:
            Dictionary containing decompressed embeddings and metadata
        """
        # Load metadata
        with open(base_path / 'metadata.json', 'r') as f:
            data = {'metadata': json.load(f)}
        
        data['chapters'] = {}
        chapters_path = base_path / 'chapters'
        
        # Load each chapter
        for chapter_dir in chapters_path.iterdir():
            if chapter_dir.is_dir():
                chapter_name = chapter_dir.name
                
                # Load chapter embedding
                with open(chapter_dir / 'chapter_embedding.bin', 'rb') as f:
                    chapter_emb = self.decompress_embedding(
                        f.read(), 
                        shape=(dimensionality,)
                    )
                
                # Load chunks
                chunks_path = chapter_dir / 'chunks'
                with open(chunks_path / 'texts.json', 'r') as f:
                    chunk_texts = json.load(f)
                
                chunk_embeddings = []
                for chunk_file in sorted(chunks_path.glob('chunk_*.bin')):
                    with open(chunk_file, 'rb') as f:
                        chunk_emb = self.decompress_embedding(
                            f.read(),
                            shape=(dimensionality,)
                        )
                        chunk_embeddings.append(chunk_emb)
                
                data['chapters'][chapter_name] = {
                    'chapter_embedding': chapter_emb,
                    'chunks': {
                        'texts': chunk_texts,
                        'embeddings': chunk_embeddings
                    }
                }
        
        return data 