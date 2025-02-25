from google.cloud import firestore
from google.auth.credentials import AnonymousCredentials
from src.config.firebase_config import FIREBASE_CONFIG
import logging
import requests
import json
from typing import Dict, Any, Optional

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
            self.base_url = FIREBASE_CONFIG.get('database_url')
            self.api_key = FIREBASE_CONFIG.get('api_key')
            
            if not self.base_url or not self.api_key:
                logger.error("Firebase configuration missing")
                raise ValueError("Firebase configuration missing")

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

    def get_data(self, path: str) -> Optional[Dict[str, Any]]:
        """Get data from Firebase"""
        try:
            url = f"{self.base_url}/{path}.json?auth={self.api_key}"
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting data from Firebase: {e}")
            return None

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

    def update_data(self, path: str, data: Dict[str, Any]) -> bool:
        """Update data in Firebase"""
        try:
            url = f"{self.base_url}/{path}.json?auth={self.api_key}"
            response = requests.patch(url, json=data)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error updating data in Firebase: {e}")
            return False

    def batch_update(self, data_dict: Dict[str, Dict[str, Any]]) -> bool:
        """
        Update multiple paths in a single batch operation
        
        Args:
            data_dict: Dictionary mapping paths to data objects
                       e.g. {"users/123": {"name": "John"}, "scores/123": {"value": 100}}
        """
        try:
            # Convert to Firebase multi-path update format
            batch_data = {}
            for path, data in data_dict.items():
                # Remove leading slash if present
                path = path.lstrip('/')
                # Replace / with . for Firebase multi-path update
                normalized_path = path.replace('/', '.')
                batch_data[normalized_path] = data
            
            # Send batch update
            url = f"{self.base_url}/.json?auth={self.api_key}"
            response = requests.patch(url, json=batch_data)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error performing batch update in Firebase: {e}")
            return False
