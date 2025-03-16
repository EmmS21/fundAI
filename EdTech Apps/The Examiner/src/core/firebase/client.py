from google.cloud import firestore
from google.auth.credentials import AnonymousCredentials
import logging
import requests
import json
import os
import time
from typing import Dict, Any, Optional
import firebase_admin
from firebase_admin import credentials, auth, firestore as admin_firestore

logger = logging.getLogger(__name__)

# Hardcoded configuration - will be obfuscated when compiled
_FIREBASE_CONFIG = {
    "projectId": "adalchemyai-432120",
    "api_key": "AIzaSyA7A_tx7F6xVMb2sp9E8kQizGW7N3lINTs",
    "database_url": "https://adalchemyai-432120.firebaseio.com"
}

class FirebaseClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            try:
                # Initialize Firebase Admin SDK (server-side)
                # This is used for admin operations and verification
                try:
                    self.app = firebase_admin.get_app()
                except ValueError:
                    # Initialize with project ID
                    cred = credentials.ApplicationDefault()
                    self.app = firebase_admin.initialize_app(cred, {
                        'projectId': _FIREBASE_CONFIG['projectId']
                    })
                
                self.db = admin_firestore.client()
                self.base_url = _FIREBASE_CONFIG['database_url']
                self.api_key = _FIREBASE_CONFIG['api_key']
                
                # Anonymous authentication state
                self.user_id = None
                self.id_token = None
                self.refresh_token = None
                self.token_expiry = 0
                
                # Authenticate anonymously on initialization
                if not self._authenticate_anonymously():
                    raise ValueError("Failed to authenticate anonymously with Firebase")
                
                self._initialized = True
                logger.info("Firebase client initialized successfully")
            except Exception as e:
                logger.error(f"Firebase initialization error: {e}")
                raise ValueError(f"Firebase initialization failed: {e}")

    def _authenticate_anonymously(self):
        """Authenticate anonymously with Firebase"""
        try:
            # Use REST API for anonymous authentication
            auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={self.api_key}"
            payload = {"returnSecureToken": True}
            response = requests.post(auth_url, json=payload)
            
            if response.status_code == 200:
                auth_data = response.json()
                self.user_id = auth_data['localId']
                self.id_token = auth_data['idToken']
                self.refresh_token = auth_data['refreshToken']
                # Calculate token expiry (tokens valid for 1 hour)
                self.token_expiry = time.time() + int(auth_data['expiresIn'])
                logger.info(f"Anonymous authentication successful. User ID: {self.user_id}")
                return True
            else:
                logger.error(f"Anonymous authentication failed: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error during anonymous authentication: {e}")
            return False

    def _ensure_authenticated(self):
        """Ensure we have a valid authentication token"""
        # If token is expired or will expire in the next 5 minutes
        if time.time() > (self.token_expiry - 300) or not self.id_token:
            # Try to refresh the token
            if self.refresh_token:
                self._refresh_token()
            else:
                # If no refresh token, authenticate again
                self._authenticate_anonymously()
        
        return self.id_token is not None

    def _refresh_token(self):
        """Refresh the authentication token"""
        try:
            refresh_url = f"https://securetoken.googleapis.com/v1/token?key={self.api_key}"
            payload = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            }
            response = requests.post(refresh_url, json=payload)
            
            if response.status_code == 200:
                token_data = response.json()
                self.id_token = token_data['id_token']
                self.refresh_token = token_data['refresh_token']
                self.token_expiry = time.time() + int(token_data['expires_in'])
                logger.info("Token refreshed successfully")
                return True
            else:
                logger.error(f"Token refresh failed: {response.text}")
                # If refresh fails, try to authenticate again
                return self._authenticate_anonymously()
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return self._authenticate_anonymously()

    def update_data(self, collection: str, data: dict) -> dict:
        """Update data in Firestore"""
        try:
            if not self._ensure_authenticated():
                raise ValueError("Not authenticated")
                
            # Add user_id to the data for security rules
            data['user_id'] = self.user_id
            
            # Add a new document with auto-generated ID
            doc_ref = self.db.collection(collection).add(data)
            logger.info(f"Document added to {collection}")
            return {"id": doc_ref[1].id}
        except Exception as e:
            logger.error(f"Firestore operation failed: {e}")
            raise

    def get_collection(self, name: str):
        """Get a collection reference with proper prefix"""
        if not self._ensure_authenticated():
            raise ValueError("Not authenticated")
        return self.db.collection(f"examiner-{name}")

    def set_data(self, path: str, data: dict) -> dict:
        """Set data at specified path"""
        if not self._ensure_authenticated():
            raise ValueError("Not authenticated")
            
        # Add user_id to the data for security rules
        data['user_id'] = self.user_id
        
        return self._make_request('PUT', path, data)

    def get_data(self, path: str) -> Optional[Dict[str, Any]]:
        """Get data from Firebase"""
        try:
            if not self._ensure_authenticated():
                raise ValueError("Not authenticated")
                
            # Add auth token to request
            url = f"{self.base_url}/{path}.json?auth={self.id_token}"
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting data from Firebase: {e}")
            return None

    def _make_request(self, method: str, path: str, data: dict = None) -> dict:
        """Make a request to Firebase REST API"""
        if not self._ensure_authenticated():
            raise ValueError("Not authenticated")
            
        url = f"https://firestore.googleapis.com/v1/projects/{_FIREBASE_CONFIG['projectId']}/databases/(default)/documents"
        params = {'auth': self.id_token}
        
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
            if not self._ensure_authenticated():
                raise ValueError("Not authenticated")
                
            # Add user_id to the data for security rules
            data['user_id'] = self.user_id
            
            url = f"{self.base_url}/{path}.json?auth={self.id_token}"
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
            if not self._ensure_authenticated():
                raise ValueError("Not authenticated")
                
            # Add user_id to each data object for security rules
            for path, data in data_dict.items():
                data['user_id'] = self.user_id
            
            # Convert to Firebase multi-path update format
            batch_data = {}
            for path, data in data_dict.items():
                # Remove leading slash if present
                path = path.lstrip('/')
                # Replace / with . for Firebase multi-path update
                normalized_path = path.replace('/', '.')
                batch_data[normalized_path] = data
            
            # Send batch update
            url = f"{self.base_url}/.json?auth={self.id_token}"
            response = requests.patch(url, json=batch_data)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error performing batch update in Firebase: {e}")
            return False

    def get_user_id(self) -> str:
        """Get the current user ID"""
        self._ensure_authenticated()
        return self.user_id
