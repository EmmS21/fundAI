import hashlib
import json
import zlib
import base64
import logging
from typing import Dict, Any, Tuple, List, Optional

logger = logging.getLogger(__name__)

class DiffUtil:
    """Utility for calculating and applying diffs for large files"""
    
    @staticmethod
    def calculate_hash(data: bytes) -> str:
        """Calculate SHA-256 hash of data"""
        return hashlib.sha256(data).hexdigest()
    
    @staticmethod
    def chunk_data(data: bytes, chunk_size: int = 1024 * 64) -> List[Tuple[str, bytes]]:
        """Split data into chunks and calculate hash for each chunk"""
        chunks = []
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            chunk_hash = DiffUtil.calculate_hash(chunk)
            chunks.append((chunk_hash, chunk))
        return chunks
    
    @staticmethod
    def create_signature(data: bytes) -> Dict[str, Any]:
        """Create a signature of the data for efficient diff calculation"""
        chunks = DiffUtil.chunk_data(data)
        return {
            'total_hash': DiffUtil.calculate_hash(data),
            'chunk_hashes': [h for h, _ in chunks],
            'size': len(data)
        }
    
    @staticmethod
    def calculate_diff(old_data: bytes, new_data: bytes) -> Dict[str, Any]:
        """Calculate the difference between old and new data"""
        if not old_data:
            # If old data is empty, return the full new data
            compressed = zlib.compress(new_data)
            return {
                'type': 'full',
                'data': base64.b64encode(compressed).decode('utf-8'),
                'compressed': True,
                'target_hash': DiffUtil.calculate_hash(new_data),
                'size': len(new_data)
            }
            
        # If data is identical, return empty diff
        if DiffUtil.calculate_hash(old_data) == DiffUtil.calculate_hash(new_data):
            return {
                'type': 'identical',
                'target_hash': DiffUtil.calculate_hash(new_data),
                'size': len(new_data)
            }
            
        # For larger files, use chunk-based diff
        old_chunks = DiffUtil.chunk_data(old_data)
        new_chunks = DiffUtil.chunk_data(new_data)
        
        # Create lookup for old chunks
        old_chunk_map = {h: chunk for h, chunk in old_chunks}
        
        # Calculate operations needed to transform old to new
        operations = []
        for chunk_hash, chunk in new_chunks:
            if chunk_hash in old_chunk_map:
                # Chunk exists in old data, just reference it
                operations.append({
                    'op': 'copy',
                    'hash': chunk_hash
                })
            else:
                # New chunk, include the data
                compressed = zlib.compress(chunk)
                operations.append({
                    'op': 'add',
                    'data': base64.b64encode(compressed).decode('utf-8'),
                    'hash': chunk_hash
                })
        
        return {
            'type': 'chunked',
            'operations': operations,
            'target_hash': DiffUtil.calculate_hash(new_data),
            'size': len(new_data)
        }
    
    @staticmethod
    def apply_diff(old_data: bytes, diff: Dict[str, Any]) -> Optional[bytes]:
        """Apply a diff to old data to get new data"""
        try:
            if diff['type'] == 'identical':
                return old_data
                
            if diff['type'] == 'full':
                # Full replacement
                compressed_data = base64.b64decode(diff['data'])
                return zlib.decompress(compressed_data)
                
            if diff['type'] == 'chunked':
                # Chunk-based diff
                old_chunks = DiffUtil.chunk_data(old_data)
                old_chunk_map = {h: chunk for h, chunk in old_chunks}
                
                # Apply operations
                result = bytearray()
                for op in diff['operations']:
                    if op['op'] == 'copy':
                        if op['hash'] in old_chunk_map:
                            result.extend(old_chunk_map[op['hash']])
                        else:
                            logger.error(f"Missing chunk with hash {op['hash']}")
                            return None
                    elif op['op'] == 'add':
                        compressed_data = base64.b64decode(op['data'])
                        chunk = zlib.decompress(compressed_data)
                        result.extend(chunk)
                
                # Verify the result
                result_bytes = bytes(result)
                if DiffUtil.calculate_hash(result_bytes) != diff['target_hash']:
                    logger.error("Hash verification failed after applying diff")
                    return None
                    
                return result_bytes
                
            logger.error(f"Unknown diff type: {diff['type']}")
            return None
            
        except Exception as e:
            logger.error(f"Error applying diff: {e}")
            return None
