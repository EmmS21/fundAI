import os
import logging
import json
import base64
from typing import Optional, Dict, Tuple, Any
import uuid

# Platform-specific imports
try:
    # Try to import keyring for secure credential storage
    import keyring # type: ignore
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

try:
    # For encryption
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

from src.utils.hardware_identifier import HardwareIdentifier

# Set up logging
logger = logging.getLogger(__name__)

class CredentialManager:
    """
    Secure credential manager for storing and retrieving MongoDB connection details.
    Uses system keychain when available, with fallback to hardware-derived key encryption.
    """
    _instance = None
    
    # Constants
    APP_NAME = "ExamAssistant"
    CREDENTIAL_KEY = "mongodb_uri"
    CONFIG_FILE = os.path.expanduser("~/.config/exam-assistant/credentials.enc")
    
    def __new__(cls):
        """Singleton pattern to ensure only one instance exists"""
        if cls._instance is None:
            cls._instance = super(CredentialManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the credential manager and detect available secure storage methods"""
        if self.initialized:
            return
            
        # Check available storage methods
        self.keyring_available = KEYRING_AVAILABLE
        self.encryption_available = CRYPTO_AVAILABLE
        
        # Ensure config directory exists
        os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)
        
        self.initialized = True
        logger.info(f"Credential Manager initialized. Keyring: {self.keyring_available}, Encryption: {self.encryption_available}")
    
    def store_credentials(self, uri: str, db_name: str) -> bool:
        """
        Store MongoDB credentials securely.
        
        Args:
            uri: MongoDB connection URI
            db_name: Database name
            
        Returns:
            bool: True if credentials were stored successfully
        """
        # Create credential object
        credentials = {
            "uri": uri,
            "db_name": db_name,
            "timestamp": str(uuid.uuid4())  # Add uniqueness to prevent replay attacks
        }
        
        # First try system keychain
        if self.keyring_available:
            try:
                # Store the full credential object as JSON
                keyring.set_password(self.APP_NAME, self.CREDENTIAL_KEY, json.dumps(credentials))
                logger.info("Credentials stored in system keychain")
                return True
            except Exception as e:
                logger.warning(f"Failed to store credentials in keychain: {e}")
        
        # Fall back to file-based storage with encryption
        if self.encryption_available:
            try:
                # Encrypt and save to file
                encrypted_data = self._encrypt_credentials(credentials)
                with open(self.CONFIG_FILE, 'wb') as f:
                    f.write(encrypted_data)
                logger.info("Credentials stored with encryption in config file")
                return True
            except Exception as e:
                logger.error(f"Failed to store encrypted credentials: {e}")
        
        logger.error("No secure storage method available for credentials")
        return False
    
    def get_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Retrieve MongoDB credentials from secure storage.
        
        Returns:
            Tuple[str, str]: (connection_uri, db_name) or (None, None) if not found
        """
        credentials = None
        
        # First try system keychain
        if self.keyring_available:
            try:
                cred_str = keyring.get_password(self.APP_NAME, self.CREDENTIAL_KEY)
                if cred_str:
                    credentials = json.loads(cred_str)
                    logger.info("Credentials retrieved from system keychain")
            except Exception as e:
                logger.warning(f"Failed to retrieve credentials from keychain: {e}")
        
        # Fall back to file-based storage with encryption
        if not credentials and self.encryption_available and os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'rb') as f:
                    encrypted_data = f.read()
                credentials = self._decrypt_credentials(encrypted_data)
                logger.info("Credentials retrieved from encrypted config file")
            except Exception as e:
                logger.error(f"Failed to retrieve encrypted credentials: {e}")
        
        # Return the credentials if found
        if credentials and 'uri' in credentials and 'db_name' in credentials:
            return credentials['uri'], credentials['db_name']
            
        logger.warning("No credentials found in secure storage")
        return None, None
    
    def has_credentials(self) -> bool:
        """
        Check if credentials are stored.
        
        Returns:
            bool: True if credentials exist in any storage
        """
        # Check system keychain
        if self.keyring_available:
            try:
                cred_str = keyring.get_password(self.APP_NAME, self.CREDENTIAL_KEY)
                if cred_str:
                    return True
            except:
                pass
        
        # Check file-based storage
        if self.encryption_available and os.path.exists(self.CONFIG_FILE):
            return True
            
        return False
    
    def clear_credentials(self) -> bool:
        """
        Remove stored credentials from all storage locations.
        
        Returns:
            bool: True if credentials were cleared
        """
        success = False
        
        # Clear from system keychain
        if self.keyring_available:
            try:
                keyring.delete_password(self.APP_NAME, self.CREDENTIAL_KEY)
                success = True
                logger.info("Credentials cleared from system keychain")
            except:
                pass
        
        # Clear from file storage
        if os.path.exists(self.CONFIG_FILE):
            try:
                os.remove(self.CONFIG_FILE)
                success = True
                logger.info("Encrypted credentials file removed")
            except:
                pass
                
        return success
    
    def _derive_encryption_key(self) -> bytes:
        """
        Derive an encryption key from hardware characteristics.
        
        Returns:
            bytes: Derived encryption key
        """
        # Get hardware identifier
        hw_id, _ = HardwareIdentifier.get_hardware_id()
        
        # Additional sources of entropy
        user = os.environ.get('USER', '')
        home = os.path.expanduser('~')
        
        # Combine for key derivation
        seed = f"{hw_id}:{user}:{home}".encode()
        
        # Use a static salt (good enough for this purpose)
        salt = b'ExamAssistantSalt'
        
        # Derive key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(seed))
        return key
    
    def _encrypt_credentials(self, credentials: Dict[str, Any]) -> bytes:
        """
        Encrypt credentials with a hardware-derived key.
        
        Args:
            credentials: Dictionary of credential data
            
        Returns:
            bytes: Encrypted data
        """
        # Get encryption key
        key = self._derive_encryption_key()
        
        # Create Fernet cipher
        cipher = Fernet(key)
        
        # Encrypt data
        data = json.dumps(credentials).encode()
        encrypted_data = cipher.encrypt(data)
        
        return encrypted_data
    
    def _decrypt_credentials(self, encrypted_data: bytes) -> Dict[str, Any]:
        """
        Decrypt credentials with a hardware-derived key.
        
        Args:
            encrypted_data: Encrypted credential data
            
        Returns:
            Dict: Decrypted credential object
        """
        # Get encryption key
        key = self._derive_encryption_key()
        
        # Create Fernet cipher
        cipher = Fernet(key)
        
        # Decrypt data
        decrypted_data = cipher.decrypt(encrypted_data)
        credentials = json.loads(decrypted_data.decode())
        
        return credentials 