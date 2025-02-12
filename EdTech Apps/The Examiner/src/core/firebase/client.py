from google.cloud import firestore
from google.auth.credentials import AnonymousCredentials
from src.config.firebase_config import FIREBASE_CONFIG
import logging

logger = logging.getLogger(__name__)

class FirebaseClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            # Use anonymous credentials for public access
            credentials = AnonymousCredentials()
            
            # Initialize with project ID and anonymous credentials
            self.db = firestore.Client(
                project=FIREBASE_CONFIG['projectId'],
                credentials=credentials
            )
            self._initialized = True

    def update_data(self, collection: str, data: dict) -> dict:
        """Update data in Firestore"""
        try:
            # Add a new document with auto-generated ID
            doc_ref = self.db.collection(collection).add(data)
            logger.info(f"Document added to {collection}")
            return {"id": doc_ref[1].id}
        except Exception as e:
            logger.error(f"Firestore operation failed: {e}")
            raise

    def get_collection(self, name: str):
        """Get a collection reference"""
        return self.db.collection(name)

    def set_data(self, path: str, data: dict) -> dict:
        """Set data at specified path"""
        return self._make_request('PUT', path, data)

    def get_data(self, path: str) -> dict:
        """Get data from specified path"""
        return self._make_request('GET', path)

    def get_collection(self, name: str):
        """Get a collection reference with proper prefix"""
        return self.db.collection(f"examiner-{name}")

    def _make_request(self, method: str, path: str, data: dict = None) -> dict:
        """Make a request to Firebase REST API"""
        url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents"
        params = {'auth': self.api_key}
        
        try:
            if method == 'GET':
                response = requests.get(url, params=params)
            elif method == 'PUT':
                response = requests.put(url, params=params, json=data)
            elif method == 'PATCH':
                response = requests.patch(url, params=params, json=data)
            
            response.raise_for_status()
            return response.json() if response.text else {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Firebase request failed: {e}")
            raise
