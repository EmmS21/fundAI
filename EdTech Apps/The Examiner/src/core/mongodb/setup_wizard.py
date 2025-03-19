import logging
import sys
from typing import Optional
from src.core.mongodb.credential_manager import CredentialManager

logger = logging.getLogger(__name__)

class MongoDBSetupWizard:
    """
    A wizard to guide users through MongoDB setup and URI storage.
    This can be launched when MongoDB credentials are not found.
    """
    
    def __init__(self):
        self.credential_manager = CredentialManager()
        
    def run_setup(self) -> bool:
        """
        Run the MongoDB setup wizard
        
        Returns:
            bool: True if setup was successful, False otherwise
        """
        print("\n" + "="*50)
        print("MongoDB Connection Setup Wizard")
        print("="*50)
        print("\nThis wizard will help you set up your MongoDB connection.")
        print("You will need your MongoDB connection URI.")
        print("\nExample URI format: mongodb+srv://username:password@cluster.mongodb.net/database")
        
        # Check if credentials already exist
        if self.credential_manager.has_credentials():
            print("\nMongoDB credentials already exist.")
            replace = input("Do you want to replace them? (y/n): ").lower().strip()
            if replace != 'y':
                print("Setup cancelled. Using existing credentials.")
                return True
        
        # Get MongoDB URI from user
        uri = self._get_uri_from_user()
        if not uri:
            print("Setup cancelled.")
            return False
        
        # Store the URI
        if self.credential_manager.set_mongodb_uri(uri):
            print("\nMongoDB connection URI stored successfully!")
            print("The system will now use this connection for syncing content.")
            return True
        else:
            print("\nFailed to store MongoDB connection URI.")
            print("Please try again or contact support.")
            return False
    
    def _get_uri_from_user(self) -> Optional[str]:
        """
        Get MongoDB URI from user input
        
        Returns:
            str: MongoDB URI or None if cancelled
        """
        print("\nEnter your MongoDB connection URI:")
        print("(Press Enter without typing to cancel)")
        
        uri = input("> ").strip()
        
        if not uri:
            return None
            
        # Simple validation
        if not (uri.startswith("mongodb://") or uri.startswith("mongodb+srv://")):
            print("\nInvalid MongoDB URI format. URI should start with 'mongodb://' or 'mongodb+srv://'")
            retry = input("Try again? (y/n): ").lower().strip()
            if retry == 'y':
                return self._get_uri_from_user()
            else:
                return None
        
        # Confirm URI
        print(f"\nURI entered: {self._mask_uri(uri)}")
        confirm = input("Is this correct? (y/n): ").lower().strip()
        
        if confirm != 'y':
            retry = input("Try again? (y/n): ").lower().strip()
            if retry == 'y':
                return self._get_uri_from_user()
            else:
                return None
        
        return uri
    
    def _mask_uri(self, uri: str) -> str:
        """
        Mask sensitive parts of the URI for display
        
        Args:
            uri: MongoDB URI
            
        Returns:
            str: Masked URI
        """
        try:
            # Simple masking - just show the beginning and end
            if len(uri) > 30:
                return uri[:15] + "..." + uri[-15:]
            else:
                return uri
        except Exception:
            return uri


if __name__ == "__main__":
    # When run directly, launch the setup wizard
    wizard = MongoDBSetupWizard()
    success = wizard.run_setup()
    sys.exit(0 if success else 1) 