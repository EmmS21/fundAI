import logging
import requests
import json
import time
from typing import Dict, Any, Optional, List
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
                
                # Check if user document exists by hardware ID using REST API
                user_doc_id = self._get_user_document_id()
                
                if not user_doc_id:
                    # Initialize subscription for new user
                    today = datetime.now()
                    end_of_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                    
                    # Create document using REST API
                    url = f"{self.firestore_base_url}/examiner-users"
                    headers = {
                        "Authorization": f"Bearer {self.id_token}",
                        "Content-Type": "application/json"
                    }
                    
                    # Format for Firestore REST API - note the Z suffix for timestamps
                    doc_data = {
                        "fields": {
                            "subscribed": {"stringValue": "trial"},
                            "sub_end": {"stringValue": end_of_month.isoformat() + "Z"},
                            "hardware_id": {"stringValue": hardware_id},
                            "user_id": {"stringValue": self.user_id},
                            "full_name": {"stringValue": "New User"},
                            "country": {"stringValue": ""},
                            "school_level": {"stringValue": ""},
                            "birthday": {"stringValue": ""}
                        }
                    }
                    
                    # Create new document in examiner-users collection
                    doc_response = requests.post(url, headers=headers, json=doc_data)
                    
                    if doc_response.status_code in (200, 201):
                        logger.info("Created new user document with subscription data")
                    else:
                        logger.error(f"Failed to create user document: {doc_response.text}")
                
                return True
            else:
                logger.error(f"Anonymous authentication failed: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error during anonymous authentication: {e}")
            return False

    def _get_user_document(self):
        """Get the user document from Firestore"""
        try:
            self._ensure_authenticated()
            
            # Get the document ID for the current user
            doc_id = self._get_user_document_id()
            if not doc_id:
                logger.warning("No document ID found for user")
                return None
                
            # Get the document from Firestore
            url = f"https://firestore.googleapis.com/v1/projects/adalchemyai-432120/databases/(default)/documents/users/{doc_id}"
            headers = {
                "Authorization": f"Bearer {self.id_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Return the full document
            return response.json()
            
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
        Check subscription status for the current user
        
        Args:
            force_refresh: Force a refresh from the server
            
        Returns:
            dict: Subscription status containing subscribed status and end date
        """
        try:
            # Try to use cached status first (unless forced refresh)
            if not force_refresh:
                cached = self._get_cached_subscription()
                if cached:
                    logger.info("Using cached subscription status")
                    return cached
            
            # Get the document ID for the current user
            doc_id = self._get_user_document_id()
            if not doc_id:
                logger.warning("No document ID found for user")
                # Try to initialize subscription
                self.initialize_subscription()
                doc_id = self._get_user_document_id()
                if not doc_id:
                    logger.error("Failed to create or retrieve user document")
                    return {"error": "Failed to retrieve user document"}
                
            # Get the document with the subscription info
            url = f"{self.firestore_base_url}/examiner-users/{doc_id}"
            headers = {
                "Authorization": f"Bearer {self.id_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Failed to get document: {response.text}")
                return {"error": "Failed to get document"}
                
            user_doc = response.json()
            
            # Cache the document for future use
            self._cache_subscription_status(user_doc)
            
            # Log success
            logger.info(f"Successfully retrieved subscription status for user")
            
            return user_doc
            
        except Exception as e:
            logger.error(f"Error checking subscription status: {e}")
            return {"error": str(e)}
    
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
            
            # Use the examiner-users collection as in the original code
            response = requests.get(f"{self.firestore_base_url}/examiner-users", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Find document with matching hardware_id
                if 'documents' in data:
                    for doc in data['documents']:
                        if 'fields' in doc and 'hardware_id' in doc['fields']:
                            doc_hardware_id = doc['fields']['hardware_id'].get('stringValue')
                            if doc_hardware_id == hardware_id:
                                # Extract document ID from name field (last path segment)
                                name = doc.get('name', '')
                                doc_id = name.split('/')[-1] if name else None
                                logger.info(f"Found user document with ID: {doc_id}")
                                return doc_id
                
                logger.warning(f"No document with hardware_id {hardware_id} found")
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
            # Get hardware ID
            hardware_id = HardwareIdentifier.get_hardware_id()
            
            # Create document using REST API
            url = f"{self.firestore_base_url}/examiner-users"
            headers = {
                "Authorization": f"Bearer {self.id_token}",
                "Content-Type": "application/json"
            }
            
            # Calculate end of month for trial expiry
            today = datetime.now()
            end_of_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            end_of_month = end_of_month.replace(hour=23, minute=59, second=59)
            
            # Format for Firestore REST API - note the Z suffix for timestamps
            doc_data = {
                "fields": {
                    "subscribed": {"stringValue": "trial"},
                    "sub_end": {"stringValue": end_of_month.isoformat() + "Z"},
                    "hardware_id": {"stringValue": hardware_id},
                    "user_id": {"stringValue": self.user_id},
                    "full_name": {"stringValue": "New User"},
                    "country": {"stringValue": ""},
                    "school_level": {"stringValue": ""},
                    "birthday": {"stringValue": ""}
                }
            }
            
            # Create new document in examiner-users collection
            doc_response = requests.post(url, headers=headers, json=doc_data)
            
            if doc_response.status_code in (200, 201):
                logger.info("Created new user document with subscription data")
                return True
            else:
                logger.error(f"Failed to create user document: {doc_response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing subscription: {e}")
            return False

    def _get_examiner_report_doc_path_by_hardware_id(self, hardware_id: str) -> Optional[str]:
        """
        Finds the document path (e.g., projects/.../documents/examiner-reports/documentId)
        for an examiner-report based on hardware_id using Firestore REST API.
        Returns the full document path if found, else None.
        """
        self._ensure_authenticated()

        doc_path = f"{self.firestore_base_url}/examiner-reports/{hardware_id}"

        headers = {
            "Authorization": f"Bearer {self.id_token}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.get(doc_path, headers=headers)
            if response.status_code == 200:
                return doc_path 
            elif response.status_code == 404:
                return None 
            else:
                response.raise_for_status() 
        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking for examiner-report document by hardware_id {hardware_id}: {e}")
            return None

    def get_examiner_report(self, hardware_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves an examiner-report document from Firestore by hardware_id.
        Assumes hardware_id is the document ID in the 'examiner-reports' collection.
        """
        self._ensure_authenticated()
        doc_path = f"{self.firestore_base_url}/examiner-reports/{hardware_id}"
        headers = {
            "Authorization": f"Bearer {self.id_token}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.get(doc_path, headers=headers)
            if response.status_code == 200:
                return response.json() 
            elif response.status_code == 404:
                return None
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting examiner-report for hardware_id {hardware_id}: {e}")
            return None

    def create_examiner_report(self, hardware_id: str, report_data: Dict[str, Any]) -> bool:
        try:
            # Convert Python data to Firestore format
            firestore_data = {
                "fields": {
                    key: self._to_firestore_value(value)
                    for key, value in report_data.items()
                }
            }
            
            url = f"{self.firestore_base_url}/examiner-reports?documentId={hardware_id}"
            headers = {
                "Authorization": f"Bearer {self.id_token}",
                "Content-Type": "application/json"
            }
            response = requests.post(url, headers=headers, json=firestore_data)
            
            if response.status_code != 200:
                logger.error(f"Failed to create report. Status: {response.status_code}, Response: {response.text}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error creating examiner report: {e}")
            return False

    def update_examiner_report(self, hardware_id: str, updates: Dict[str, Any], new_answered_questions: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Updates an existing document in 'examiner-reports' using PATCH.
        'updates' contains fields to update directly (e.g., lastSyncTimestamp).
        'new_answered_questions' is a list of new question entries to append to the 'answeredQuestions' array.
        All data within 'updates' and 'new_answered_questions' must be Firestore REST API formatted values.
        e.g. updates = {"lastSyncTimestamp": {"timestampValue": "ISO_STRING"}}
             new_answered_questions = [{"mapValue": {"fields": {"questionID": {"stringValue": "q1"}}}}]
        """
        self._ensure_authenticated()
        doc_path = f"examiner-reports/{hardware_id}"         
        url = f"{self.firestore_base_url}/{doc_path}"
        headers = {
            "Authorization": f"Bearer {self.id_token}",
            "Content-Type": "application/json"
        }

        document_content = {"fields": {}}
        update_mask_paths = []

        for key, value_object in updates.items():
            document_content["fields"][key] = value_object
            update_mask_paths.append(key)
        
        payload: Dict[str, Any] = {}
        if document_content["fields"]:
             payload["document"] = document_content
        patch_body: Dict[str, Any] = {"fields": {}} 
        transforms = []

        for key, value_object in updates.items():
            patch_body["fields"][key] = value_object
        if new_answered_questions:
            transforms.append({
                "fieldPath": "answeredQuestions",
                "appendMissingElements": {
                    "values": new_answered_questions 
                }
            })
        
        if not patch_body["fields"] and not transforms:
            logger.info("No updates or new questions to sync for examiner_report.")
            return True 

        final_payload = {}
        if patch_body["fields"]:
            final_payload = patch_body["fields"] 

        if transforms:
            final_payload["writes"] = [{ 
                "update": {
                    "name": f"projects/{self.project_id}/databases/(default)/documents/{doc_path}",
                },
                "transform": {
                    "document": f"projects/{self.project_id}/databases/(default)/documents/{doc_path}",
                    "fieldTransforms": transforms
                }
            }]

        commit_url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents:commit"        
        commit_payload_writes = []        
        if updates: 
            update_fields_data = {}
            update_mask = []
            for key, value_object in updates.items():
                update_fields_data[key] = value_object
                update_mask.append(key)

            commit_payload_writes.append({
                "update": {
                    "name": f"projects/{self.project_id}/databases/(default)/documents/{doc_path}",
                    "fields": update_fields_data
                },
                "updateMask": {"fieldPaths": update_mask} 
            })

        if new_answered_questions:
            commit_payload_writes.append({
                "transform": {
                    "document": f"projects/{self.project_id}/databases/(default)/documents/{doc_path}",
                    "fieldTransforms": [{
                        "fieldPath": "answeredQuestions",
                        "appendMissingElements": {
                            "values": new_answered_questions
                        }
                    }]
                }
            })

        if not commit_payload_writes:
            logger.info("No updates or new questions specified for examiner_report.")
            return True

        final_commit_payload = {"writes": commit_payload_writes}

        try:
            response = requests.post(commit_url, headers=headers, json=final_commit_payload)
            
            if response.status_code == 200:
                logger.info(f"Successfully updated/transformed examiner-report for hardware_id {hardware_id} via commit.")
                return True
            else:
                logger.error(f"Failed to update examiner-report for {hardware_id} via commit: {response.status_code} - {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating examiner-report for hardware_id {hardware_id} via commit: {e}")
            return False

    def _to_firestore_value(self, py_value: Any) -> Dict[str, Any]:
        if isinstance(py_value, str):
            return {"stringValue": py_value}
        elif isinstance(py_value, bool):
            return {"booleanValue": py_value}
        elif isinstance(py_value, int):
            return {"integerValue": str(py_value)} 
        elif isinstance(py_value, float):
            return {"doubleValue": py_value}
        elif isinstance(py_value, datetime):
            return {"timestampValue": py_value.isoformat("T") + "Z"}
        elif py_value is None:
            return {"nullValue": None}
        elif isinstance(py_value, list):
            return {"arrayValue": {"values": [self._to_firestore_value(v) for v in py_value]}}
        elif isinstance(py_value, dict):
            return {"mapValue": {"fields": {k: self._to_firestore_value(v) for k, v in py_value.items()}}}
        else:
            logger.warning(f"Unsupported type for Firestore conversion: {type(py_value)}. Storing as string.")
            return {"stringValue": str(py_value)}

    def _firestore_doc_to_dict(self, firestore_doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not firestore_doc or 'fields' not in firestore_doc:
            return None
        
        py_dict = {}
        for key, firestore_value in firestore_doc['fields'].items():
            if 'stringValue' in firestore_value:
                py_dict[key] = firestore_value['stringValue']
            elif 'booleanValue' in firestore_value:
                py_dict[key] = firestore_value['booleanValue']
            elif 'integerValue' in firestore_value:
                py_dict[key] = int(firestore_value['integerValue'])
            elif 'doubleValue' in firestore_value:
                py_dict[key] = firestore_value['doubleValue']
            elif 'timestampValue' in firestore_value:
                try:
                    ts_str = firestore_value['timestampValue']
                    if ts_str.endswith('Z'):
                        ts_str = ts_str[:-1] + '+00:00'
                    py_dict[key] = datetime.fromisoformat(ts_str)
                except ValueError:
                    py_dict[key] = firestore_value['timestampValue']
            elif 'nullValue' in firestore_value:
                py_dict[key] = None
            elif 'arrayValue' in firestore_value:
                values = firestore_value['arrayValue'].get('values', [])
                py_dict[key] = [self._firestore_value_to_py(v) for v in values]
            elif 'mapValue' in firestore_value:
                py_dict[key] = self._firestore_doc_to_dict(firestore_value['mapValue']) 
        return py_dict

    def _firestore_value_to_py(self, firestore_value: Dict[str, Any]) -> Any:
        if 'stringValue' in firestore_value:
            return firestore_value['stringValue']
        elif 'booleanValue' in firestore_value:
            return firestore_value['booleanValue']
        elif 'integerValue' in firestore_value:
            return int(firestore_value['integerValue'])
        elif 'doubleValue' in firestore_value:
            return firestore_value['doubleValue']
        elif 'timestampValue' in firestore_value:
            try:
                ts_str = firestore_value['timestampValue']
                if ts_str.endswith('Z'):
                    ts_str = ts_str[:-1] + '+00:00'
                return datetime.fromisoformat(ts_str)
            except ValueError:
                return firestore_value['timestampValue']
        elif 'nullValue' in firestore_value:
            return None
        elif 'arrayValue' in firestore_value:
            values = firestore_value['arrayValue'].get('values', [])
            return [self._firestore_value_to_py(v) for v in values]
        elif 'mapValue' in firestore_value:
            return self._firestore_doc_to_dict({"fields": firestore_value['mapValue'].get('fields', {})})
        return None 
