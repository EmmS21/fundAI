import requests
from typing import Optional
import logging
import json
from src.config.firebase_config import FIREBASE_CONFIG

logger = logging.getLogger(__name__)

class FirebaseClient:
    _instance: Optional['FirebaseClient'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.base_url = f"https://{FIREBASE_CONFIG['projectId']}.firebaseio.com"
        self.api_key = FIREBASE_CONFIG['apiKey']

    def _make_request(self, method: str, path: str, data: dict = None) -> dict:
        """Make a request to Firebase REST API"""
        url = f"{self.base_url}/{path}.json"
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

    def update_data(self, path: str, data: dict) -> dict:
        """Update data at specified path"""
        return self._make_request('PATCH', path, data)

    def set_data(self, path: str, data: dict) -> dict:
        """Set data at specified path"""
        return self._make_request('PUT', path, data)

    def get_data(self, path: str) -> dict:
        """Get data from specified path"""
        return self._make_request('GET', path)

    def get_collection(self, name: str):
        """Get a collection reference with proper prefix"""
        return self.db.collection(f"examiner-{name}")
