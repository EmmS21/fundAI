import logging
import requests
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from src.utils.secure_storage import SecureStorage
from src.utils.hardware_identifier import HardwareIdentifier
from src.core.network.monitor import NetworkMonitor
from google.cloud.firestore_v1.base_query import FieldFilter
from src.data.database.operations import UserOperations
from src.utils.db import get_db_session

logger = logging.getLogger(__name__)

# Hardcoded configuration - will be obfuscated when compiled
_FIREBASE_CONFIG = {
    "projectId": "adalchemyai-432120",
    "api_key": "AIzaSyA7A_tx7F6xVMb2sp9E8kQizGW7N3lINTs",
    "database_url": "https://adalchemyai-432120.firebaseio.com"
}

class FirebaseClient:
    _instance = None
    
    # Add constants for subscription cache
    SUBSCRIPTION_CACHE_KEY = 'subscription_status'
    SUBSCRIPTION_CACHE_VALIDITY = 86400  # 24 hours in seconds
    OFFLINE_GRACE_PERIOD = 7  # days
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            try:
                # Store API key and project ID for REST operations
                self.api_key = _FIREBASE_CONFIG['api_key']
                self.project_id = _FIREBASE_CONFIG['projectId']
                
                # Base URL for Firestore REST API
                self.firestore_base_url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents"
                
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
        """Authenticate anonymously with Firebase using hardware ID"""
        try:            
            # Get hardware ID
            hardware_id = HardwareIdentifier.get_hardware_id()
            
            # Use REST API for anonymous authentication
            auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={self.api_key}"
            payload = {
                "returnSecureToken": True,
                # Include hardware ID in custom claims
                "customAttributes": json.dumps({"hardware_id": hardware_id})
            }
            response = requests.post(auth_url, json=payload)
            
            if response.status_code == 200:
                auth_data = response.json()
                self.user_id = auth_data['localId']
                self.id_token = auth_data['idToken']
                self.refresh_token = auth_data['refreshToken']
                # Calculate token expiry (tokens valid for 1 hour)
                self.token_expiry = time.time() + int(auth_data['expiresIn'])
                logger.info(f"Anonymous authentication successful. User ID: {self.user_id}")
                
                # Find or initialize user document
                user_doc = self._get_user_document()
                if not user_doc:
                    # Initialize subscription for new user
                    today = datetime.now()
                    end_of_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                    end_of_month = end_of_month.replace(hour=23, minute=59, second=59)
                    
                    subscription_data = {
                        'is_active': True,
                        'subscription_type': 'trial',
                        'subscription_expiry': end_of_month.isoformat(),
                        'hardware_id': hardware_id,
                        'user_id': self.user_id
                    }
                    
                    # Create new document in examiner-users collection
                    self.db.collection('examiner-users').document().set(subscription_data)
                    logger.info("Created new user document with subscription data")
                
                return True
            else:
                logger.error(f"Anonymous authentication failed: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error during anonymous authentication: {e}")
            return False

    def _get_user_document(self):
        """Get the user document from Firestore using hardware_id"""
        try:
            # Ensure we're authenticated
            self._ensure_authenticated()
            
            # Get hardware ID
            hardware_id = HardwareIdentifier.get_hardware_id()
            
            # Make the request to get all documents
            url = f"{self.firestore_base_url}/examiner-users"
            headers = {"Authorization": f"Bearer {self.id_token}"}
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # First, try to find document with matching hardware_id
                if 'documents' in data:
                    # Look for hardware_id match
                    for doc in data['documents']:
                        if 'fields' in doc and 'hardware_id' in doc['fields']:
                            doc_hardware_id = doc['fields']['hardware_id'].get('stringValue')
                            if doc_hardware_id == hardware_id:
                                logger.info(f"Found document with matching hardware_id: {doc['name']}")
                                # Simple print of the document
                                print("DOCUMENT FOUND:", doc)
                                
                                # Check if subscription fields exist
                                fields = doc['fields']
                                has_subscribed = 'subscribed' in fields
                                has_sub_end = 'sub_end' in fields
                                
                                # If subscription fields don't exist, add them
                                if not has_subscribed or not has_sub_end:
                                    print("First sync detected - subscription fields missing. Adding trial subscription.")
                                    
                                    # Extract document ID from the document name
                                    doc_id = doc['name'].split('/')[-1]
                                    
                                    # Calculate one month from now
                                    now = datetime.now()
                                    one_month_later = now + timedelta(days=30)
                                    sub_end_iso = one_month_later.isoformat()
                                    
                                    # Prepare update data with Firestore typed values
                                    update_data = {
                                        "fields": {
                                            "subscribed": {"stringValue": "trial"},
                                            "sub_end": {"stringValue": sub_end_iso}
                                        }
                                    }
                                    
                                    # Update the document
                                    update_url = f"{self.firestore_base_url}/examiner-users/{doc_id}"
                                    update_headers = {
                                        "Content-Type": "application/json",
                                        "Authorization": f"Bearer {self.id_token}"
                                    }
                                    # Add mask to only update these specific fields
                                    update_url += "?updateMask.fieldPaths=subscribed&updateMask.fieldPaths=sub_end"
                                    
                                    update_response = requests.patch(update_url, headers=update_headers, json=update_data)
                                    
                                    if update_response.status_code == 200:
                                        print("Successfully updated subscription fields:")
                                        print(f"- subscribed: trial")
                                        print(f"- sub_end: {sub_end_iso}")
                                        
                                        # Get the updated document
                                        updated_doc_response = requests.get(f"{self.firestore_base_url}/examiner-users/{doc_id}", headers=headers)
                                        if updated_doc_response.status_code == 200:
                                            updated_doc = updated_doc_response.json()
                                            print("UPDATED DOCUMENT:", updated_doc)
                                    else:
                                        print(f"Failed to update subscription fields: {update_response.text}")
                                
                                return doc['fields']
                    
                    # If we get here, no hardware_id match was found
                    # Try to match by full_name as a fallback
                    with get_db_session() as session:
                        user = UserOperations.get_current_user()
                        if user and user.full_name:
                            full_name = user.full_name
                            logger.info(f"Trying to find document by full_name: {full_name}")
                            
                            for doc in data['documents']:
                                if 'fields' in doc and 'full_name' in doc['fields']:
                                    doc_full_name = doc['fields']['full_name'].get('stringValue')
                                    if doc_full_name == full_name:
                                        logger.info(f"Found document with matching full_name: {doc['name']}")
                                        # Simple print of the document
                                        print("DOCUMENT FOUND:", doc)
                                        return doc['fields']
                
                # If we get here, no matching document was found by either method
                logger.warning(f"No document found with hardware_id: {hardware_id} or by full_name")
                return None
            else:
                logger.error(f"Failed to get documents: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting user document: {e}")
            return None

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

    def update_data(self, collection: str, data: dict) -> bool:
        """Update data in Firestore"""
        try:
            if not self._ensure_authenticated():
                raise ValueError("Not authenticated")
            
            # Add user_id to the data for security rules
            data['user_id'] = self.user_id
            
            # Use Firestore Admin SDK
            doc_ref = self.db.collection(collection).document()
            doc_ref.set(data)
            logger.info(f"Document updated in {collection}")
            return True
        except Exception as e:
            logger.error(f"Firestore operation failed: {e}")
            return False

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

    def check_subscription_status(self, force_refresh=False) -> dict:
        """
        Check the user's subscription status in Firebase.
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data
            
        Returns:
            dict: Subscription status information with keys:
                - is_active: bool - Whether subscription is active
                - type: str - Subscription type (monthly, annual, trial)
                - expiry_date: str - ISO format expiry date
                - cached_at: str - When this status was last verified with server
        """
        # Ensure user is authenticated
        self._ensure_authenticated()
        
        # Check if we have cached subscription data that's still valid
        cached_data = self._get_cached_subscription()
        
        if cached_data and not force_refresh:
            # If we have cached data and it's still valid, use it
            return cached_data
        
        try:
            # Fetch subscription data from Firebase
            user_id = self.get_user_id()
            path = f"users/{user_id}/subscription"
            subscription_data = self.get_data(path)
            
            if not subscription_data:
                # No subscription data found
                status = {
                    'is_active': False,
                    'type': 'none',
                    'expiry_date': None,
                    'cached_at': datetime.now().isoformat()
                }
            else:
                # Parse expiry date
                expiry_date = subscription_data.get('expiry_date')
                
                # Check if subscription is active
                is_active = False
                if expiry_date:
                    # Parse the expiry date string to datetime
                    if isinstance(expiry_date, str):
                        expiry_dt = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
                    else:
                        # Assume it's already a datetime or timestamp
                        expiry_dt = datetime.fromtimestamp(expiry_date)
                        
                    # Check if subscription is still valid
                    is_active = datetime.now() < expiry_dt
                
                status = {
                    'is_active': is_active,
                    'type': subscription_data.get('type', 'none'),
                    'expiry_date': expiry_date,
                    'cached_at': datetime.now().isoformat()
                }
            
            # Cache the status
            self._cache_subscription_status(status)
            
            return status
            
        except Exception as e:
            logger.error(f"Error checking subscription status: {e}")
            
            # If we have cached data, use it as fallback
            if cached_data:
                return cached_data
                
            # Otherwise return inactive status
            return {
                'is_active': False,
                'type': 'error',
                'expiry_date': None,
                'cached_at': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def _get_cached_subscription(self) -> dict:
        """Get cached subscription status if available and valid"""
        try:            
            storage = SecureStorage()
            hardware_id = HardwareIdentifier.get_hardware_id()
            
            # Use both hardware ID and user ID for cache key
            cache_key = f"subscription_status_{hardware_id}_{self.user_id}"
            cached_json = storage.get(cache_key)
            
            if not cached_json:
                return None
                
            cached_data = json.loads(cached_json)
            cached_at = datetime.fromisoformat(cached_data.get('cached_at', '').replace('Z', '+00:00'))
            
            # Check if cache is still valid
            cache_age = (datetime.now() - cached_at).total_seconds()
            
            # For offline grace period, we use a much longer validity
            network_monitor = NetworkMonitor()
            
            if network_monitor.get_status() == 'offline':
                # If offline, use the offline grace period (in days)
                max_age = self.OFFLINE_GRACE_PERIOD * 24 * 60 * 60
            else:
                # If online, use normal cache validity
                max_age = self.SUBSCRIPTION_CACHE_VALIDITY
                
            if cache_age <= max_age:
                return cached_data
                
            return None
            
        except Exception as e:
            print(f"Error getting cached subscription: {e}")
            return None
    
    def _cache_subscription_status(self, status: dict) -> bool:
        """Save subscription status to local cache"""
        try:            
            storage = SecureStorage()
            hardware_id = HardwareIdentifier.get_hardware_id()
            
            # Use both hardware ID and user ID for cache key
            cache_key = f"subscription_status_{hardware_id}_{self.user_id}"
            cached_json = json.dumps(status)
            storage.set(cache_key, cached_json)
            return True
        except Exception as e:
            print(f"Error caching subscription status: {e}")
            return False

    def _get_user_document_id(self) -> Optional[str]:
        """Find the user's document ID using Firestore REST API"""
        try:
            hardware_id = HardwareIdentifier.get_hardware_id()
            
            # Add auth token to headers
            headers = {
                'Authorization': f'Bearer {self.id_token}',
                'Content-Type': 'application/json'
            }
            
            # Get all documents in examiner-users collection
            response = requests.get(f"{self.firestore_base_url}/examiner-users", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Find document with matching hardware_id
                if 'documents' in data:
                    for doc in data['documents']:
                        if 'fields' in doc and 'hardware_id' in doc['fields']:
                            if doc['fields']['hardware_id'].get('stringValue') == hardware_id:
                                # Extract document ID from name field (last path segment)
                                name = doc.get('name', '')
                                return name.split('/')[-1] if name else None
                return None
            else:
                logger.error(f"Failed to get documents: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error finding user document: {e}")
            return None

    def initialize_subscription(self):
        """Initialize subscription fields for user if they don't exist"""
        try:
            # Find user's document
            doc_id = self._get_user_document_id()
            if not doc_id:
                logger.warning("Could not find user document")
                return False

            # Headers for Firestore REST API
            headers = {
                'Authorization': f'Bearer {self.id_token}',
                'Content-Type': 'application/json'
            }

            # Get current document data
            doc_url = f"{self.firestore_base_url}/examiner-users/{doc_id}"
            response = requests.get(doc_url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to get document: {response.text}")
                return False
                
            doc_data = response.json()

            # Check if subscription fields exist
            has_subscription = False
            if 'fields' in doc_data:
                has_subscription = 'subscription_type' in doc_data['fields']

            # Only initialize if subscription fields don't exist
            if not has_subscription:
                # Calculate end of month for trial expiry
                today = datetime.now()
                end_of_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                end_of_month = end_of_month.replace(hour=23, minute=59, second=59)

                # Create subscription fields in Firestore format
                update_data = {
                    "fields": {
                        "is_active": {"booleanValue": True},
                        "subscription_type": {"stringValue": "trial"},
                        "subscription_expiry": {"stringValue": end_of_month.isoformat()}
                    }
                }

                # Use PATCH to update specific fields
                update_response = requests.patch(
                    doc_url, 
                    headers=headers,
                    json=update_data
                )
                
                if update_response.status_code in (200, 201):
                    logger.info(f"Initialized subscription fields for user document {doc_id}")
                    return True
                else:
                    logger.error(f"Failed to update subscription: {update_response.text}")
                    return False

            return True  # Fields already exist
        except Exception as e:
            logger.error(f"Error initializing subscription: {e}")
            return False
