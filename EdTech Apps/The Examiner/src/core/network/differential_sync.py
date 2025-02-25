import logging
import os
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from src.utils.diff_util import DiffUtil
from src.utils.hardware_identifier import HardwareIdentifier

logger = logging.getLogger(__name__)

class DifferentialSyncManager:
    """Manages differential sync for large files like paper content"""
    
    def __init__(self, firebase_client=None):
        self.firebase = firebase_client
        self.metadata_dir = os.path.join("src", "data", "cache", "metadata")
        os.makedirs(self.metadata_dir, exist_ok=True)
    
    def _get_metadata_path(self, file_id: str) -> str:
        """Get the path to the metadata file for a given file ID"""
        return os.path.join(self.metadata_dir, f"{file_id}.meta")
    
    def _save_metadata(self, file_id: str, metadata: Dict[str, Any]) -> None:
        """Save metadata for a file"""
        try:
            with open(self._get_metadata_path(file_id), 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metadata for {file_id}: {e}")
    
    def _load_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Load metadata for a file"""
        try:
            metadata_path = self._get_metadata_path(file_id)
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Error loading metadata for {file_id}: {e}")
            return None
    
    def prepare_upload(self, file_id: str, data: bytes) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Prepare data for differential upload
        
        Returns:
            Tuple containing (metadata, sync_data)
        """
        # Load existing metadata if available
        metadata = self._load_metadata(file_id) or {
            'file_id': file_id,
            'version': 0,
            'last_sync': None,
            'size': 0,
            'hash': None
        }
        
        # Calculate current hash
        current_hash = DiffUtil.calculate_hash(data)
        
        # Check if content has changed
        if metadata.get('hash') == current_hash:
            # No changes, just return metadata
            return metadata, {
                'type': 'no_change',
                'file_id': file_id,
                'version': metadata['version']
            }
        
        # Get previous version data if available
        previous_data = b''
        if metadata.get('hash'):
            # In a real implementation, we would load the previous version
            # For now, we'll assume we don't have it and send full data
            pass
        
        # Calculate diff
        diff = DiffUtil.calculate_diff(previous_data, data)
        
        # Update metadata
        metadata['version'] += 1
        metadata['last_sync'] = datetime.now().isoformat()
        metadata['size'] = len(data)
        metadata['hash'] = current_hash
        
        # Save updated metadata
        self._save_metadata(file_id, metadata)
        
        # Prepare sync data
        sync_data = {
            'file_id': file_id,
            'version': metadata['version'],
            'diff': diff,
            'hardware_id': HardwareIdentifier.get_hardware_id()[0]
        }
        
        return metadata, sync_data
    
    def sync_file(self, file_id: str, data: bytes) -> bool:
        """
        Sync a file using differential sync
        
        Args:
            file_id: Unique identifier for the file
            data: File content as bytes
            
        Returns:
            bool: True if sync was successful
        """
        if not self.firebase:
            logger.error("Firebase client not initialized")
            return False
            
        try:
            # Prepare data for sync
            metadata, sync_data = self.prepare_upload(file_id, data)
            
            # If no changes, nothing to sync
            if sync_data['type'] == 'no_change':
                logger.info(f"No changes detected for {file_id}, skipping sync")
                return True
            
            # Upload to Firebase
            path = f"paper-cache/{file_id}"
            self.firebase.update_data(path, sync_data)
            
            logger.info(f"Successfully synced {file_id} (version {metadata['version']})")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing file {file_id}: {e}")
            return False
    
    def download_file(self, file_id: str, local_data: bytes = None) -> Optional[bytes]:
        """
        Download a file using differential sync
        
        Args:
            file_id: Unique identifier for the file
            local_data: Current local data (if any)
            
        Returns:
            bytes: Updated file content or None if download failed
        """
        if not self.firebase:
            logger.error("Firebase client not initialized")
            return None
            
        try:
            # Get remote metadata
            path = f"paper-cache/{file_id}"
            remote_data = self.firebase.get_data(path)
            
            if not remote_data:
                logger.warning(f"No remote data found for {file_id}")
                return None
                
            # Load local metadata
            local_metadata = self._load_metadata(file_id)
            
            # If we have the same version, no need to download
            if local_metadata and local_metadata.get('version') == remote_data.get('version'):
                logger.info(f"Local version of {file_id} is up to date")
                return local_data
                
            # Apply diff to get updated content
            diff = remote_data.get('diff')
            if not diff:
                logger.error(f"No diff found in remote data for {file_id}")
                return None
                
            updated_data = DiffUtil.apply_diff(local_data or b'', diff)
            if not updated_data:
                logger.error(f"Failed to apply diff for {file_id}")
                return None
                
            # Update local metadata
            new_metadata = {
                'file_id': file_id,
                'version': remote_data['version'],
                'last_sync': datetime.now().isoformat(),
                'size': len(updated_data),
                'hash': DiffUtil.calculate_hash(updated_data)
            }
            self._save_metadata(file_id, new_metadata)
            
            logger.info(f"Successfully downloaded {file_id} (version {new_metadata['version']})")
            return updated_data
            
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            return None
