import os
import json
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from ..utils.hardware_identifier import HardwareIdentifier

logger = logging.getLogger(__name__)

class SecureStorage:
    """
    Utility for securely storing sensitive data on device.
    Uses hardware-bound encryption to protect stored data.
    """
    
    STORAGE_DIR = os.path.join("src", "data", "secure")
    
    def __init__(self):
        """Initialize the secure storage"""
        # Create storage directory if it doesn't exist
        os.makedirs(self.STORAGE_DIR, exist_ok=True)
        
        # Get hardware identifier for deriving encryption key
        self.hardware_id = HardwareIdentifier.get_or_create_hardware_id()
        
        # Generate encryption key from hardware ID
        self.key = self._derive_key(self.hardware_id)
        self.cipher = Fernet(self.key)
    
    def _derive_key(self, seed: str) -> bytes:
        """
        Derive encryption key from seed string (hardware ID)
        
        Args:
            seed: Seed string for key derivation
            
        Returns:
            bytes: A valid Fernet key
        """
        # Use a fixed salt - this is OK since we have a hardware-specific seed
        salt = b'TheExaminerApp'
        
        # Hash the seed to make it suitable for key derivation
        seed_bytes = seed.encode()
        
        # Generate a key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        # Derive key and convert to Fernet format
        key_bytes = kdf.derive(seed_bytes)
        return base64.urlsafe_b64encode(key_bytes)
    
    def get(self, key: str) -> str:
        """
        Get a value from secure storage
        
        Args:
            key: The storage key
            
        Returns:
            str: The stored value, or None if not found
        """
        try:
            file_path = os.path.join(self.STORAGE_DIR, f"{key}.enc")
            
            if not os.path.exists(file_path):
                return None
                
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()
                
            # Decrypt the data
            decrypted_data = self.cipher.decrypt(encrypted_data)
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error reading from secure storage: {e}")
            return None
    
    def set(self, key: str, value: str) -> bool:
        """
        Store a value in secure storage
        
        Args:
            key: The storage key
            value: The value to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            file_path = os.path.join(self.STORAGE_DIR, f"{key}.enc")
            
            # Encrypt the data
            encrypted_data = self.cipher.encrypt(value.encode('utf-8'))
            
            # Write to file
            with open(file_path, 'wb') as f:
                f.write(encrypted_data)
                
            return True
            
        except Exception as e:
            logger.error(f"Error writing to secure storage: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from secure storage
        
        Args:
            key: The storage key
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            file_path = os.path.join(self.STORAGE_DIR, f"{key}.enc")
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
            return True
            
        except Exception as e:
            logger.error(f"Error deleting from secure storage: {e}")
            return False 