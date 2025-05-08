from src.data.database.operations import PaperCacheOperations, UserOperations
from src.utils.db import get_db_session
from typing import Any, List, Dict, Optional
import threading
import time
import os
import json
import logging
import sqlite3
from datetime import datetime, timedelta, date
import uuid
import requests
from PIL import Image
import hashlib
from src.core.network.monitor import NetworkStatus, NetworkMonitor
from src.core.queue_manager import QueuePriority
from src.data.database.models import Base as BaseModel
from src.core.firebase.client import FirebaseClient
import re
from src.core.mongodb.client import MongoDBClient
import random
from src.data.database.models import QuestionResponse, User, ExamResult
from bs4 import BeautifulSoup
import mimetypes
from bson import ObjectId # Make sure this import exists at the top
import pprint # Import pprint for prettier dictionary logging
# Import SQLAlchemy components and the specific model
from src.utils.db import get_db_session # Get session factory
from src.data.database.models import CachedQuestion # Import the ORM model
from src.data.database.models import CachedAnswer # Ensure models are imported


logger = logging.getLogger(__name__)

class CacheStatus:
    """Enumeration of cache statuses"""
    FRESH = "fresh"       
    STALE = "stale"        
    EXPIRED = "expired"   
    INVALID = "invalid"   

class SubscriptionStatus:
    """Enumeration of subscription statuses"""
    ACTIVE = "active"        # Subscription is active
    EXPIRING = "expiring"    # Subscription will expire soon (within warning period)
    EXPIRED = "expired"      # Subscription has expired

class CacheProgressStatus:
    """Enumeration of cache progress statuses"""
    IDLE = "idle"            # No active caching operations
    SYNCING = "syncing"      # Actively syncing content
    DOWNLOADING = "downloading"  # Downloading new content
    ERROR = "error"          # Error during sync/download

class CacheManager:
    _instance = None
    
    # Storage paths
    CACHE_BASE_DIR = os.path.join("src", "data", "cache")
    METADATA_DIR = os.path.join(CACHE_BASE_DIR, "metadata")
    ASSETS_DIR = os.path.join(CACHE_BASE_DIR, "assets")
    QUESTIONS_DIR = os.path.join(CACHE_BASE_DIR, "questions")
    ANSWERS_DIR = os.path.join(CACHE_BASE_DIR, "answers")
    
    # Cache settings
    MAX_CACHE_SIZE_MB = 500  
    CHECK_INTERVAL = 3600    
    PAPERS_PER_SUBJECT = 2   # Changed from 5 to 2 years
    
    # Subscription settings
    SUBSCRIPTION_CACHE_TTL = 3600  # Cache subscription status for 1 hour
    SUBSCRIPTION_WARNING_DAYS = 7  # Warn when 7 days from expiration

    # Valid subscription types
    VALID_SUBSCRIPTION_TYPES = ["trial", "annual", "monthly"]

    DB_FILE = "cache.db"
    
    def __new__(cls):
        """Singleton pattern to ensure only one instance exists"""
        if cls._instance is None:
            cls._instance = super(CacheManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the cache manager"""
        # Prevent re-initialization if using Singleton pattern correctly
        if hasattr(self, 'initialized') and self.initialized: 
            return
            
        # --- FIX: Initialize logger FIRST ---
        # Assign logger to the instance immediately
        self.logger = logging.getLogger(__name__) 
        # --- End FIX ---

        # Proceed with the rest of the initialization
        self.logger.debug("Initializing CacheManager...") # Use the logger now

        # Create cache directories 
        os.makedirs(self.METADATA_DIR, exist_ok=True)
        os.makedirs(self.ASSETS_DIR, exist_ok=True)
        os.makedirs(self.QUESTIONS_DIR, exist_ok=True)
        os.makedirs(self.ANSWERS_DIR, exist_ok=True)
        
        # Initialize other attributes BEFORE potentially calling methods that use them
        self.mongodb_client = MongoDBClient()
        self.network_monitor = NetworkMonitor()
        self.running = False
        self.thread = None
        self.subscription_cache = None
        self.subscription_cache_time = 0
        self.db_path = os.path.join(os.path.dirname(__file__), self.DB_FILE)
        self.conn = None
        self.lock = threading.RLock() 
        self.global_metadata_lock = threading.Lock() 
        self.ttl_fresh = 3600 
        self.ttl_stale = 86400 

        # Initialize database AFTER basic attributes are set
        self._ensure_tables() 
        self._initialize_db() 
        
        # Connect signal AFTER essential attributes are set
        self.network_monitor.status_changed.connect(self._handle_network_change)
        
        # Mark as initialized at the very end
        self.initialized = True
        self.logger.info("Cache Manager initialized") 
    
    def _initialize_db(self):
        """Initialize the SQLite database"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = self.conn.cursor()
            
            # Create the cache table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                sync_status TEXT DEFAULT 'synced'
            )
            ''')
            
            # Create index for faster lookups
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON cache(timestamp)')
            
            self.conn.commit()
            logger.info("Cache database initialized")
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
        
    def start(self):
        """Start the cache manager background thread"""
        if self.thread and self.thread.is_alive():
            logger.info("Cache Manager already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("Cache Manager started")
        
        # Immediately check for updates in a separate thread to avoid blocking
        update_thread = threading.Thread(target=self._initial_update_check, daemon=True)
        update_thread.start()
        
    def _initial_update_check(self):
        """Perform an immediate check for updates on startup"""
        try:
            logger.info("Performing initial content check on startup...")
            time.sleep(3)  # Delay to let other systems initialize
            
            # Only proceed if subscription is active - do this check first
            subscription_status = self._verify_subscription()
            if subscription_status != SubscriptionStatus.ACTIVE:
                logger.warning(f"Subscription not active (status: {subscription_status}), skipping content check")
                return
            
            logger.info("Subscription is active, checking network status...")    
                
            # Force a fresh network status check
            network_status = self.network_monitor.force_check()
            logger.info(f"Network status check result: {network_status}")
            
            # If NetworkMonitor reports offline but we suspect we're online, do an additional check
            if network_status != NetworkStatus.ONLINE:
                logger.info("NetworkMonitor reports offline status, performing additional connection test...")
                # Try to connect to a reliable service
                try:
                    import socket
                    socket.create_connection(("8.8.8.8", 53), timeout=1)
                    # If we get here, we're actually online
                    logger.info("Additional connection test successful - we are actually online")
                    network_status = NetworkStatus.ONLINE
                except Exception as e:
                    logger.warning(f"Additional connection test failed: {e}")
            
            # Only proceed if we're online
            if network_status == NetworkStatus.ONLINE:
                logger.info("Network is online, checking MongoDB credentials...")
                
                # Check MongoDB connection
                if self.mongodb_client.has_credentials():
                    logger.info("MongoDB credentials found, connecting...")
                    
                    # Connect to MongoDB if not already connected
                    if not self.mongodb_client.connected:
                        connection_result = self.mongodb_client.connect()
                        logger.info(f"MongoDB connection result: {connection_result}")
                    
                    if self.mongodb_client.connected:
                        logger.info("MongoDB connected, checking for new content...")
                        # Directly call the method to check for updates
                        self._check_for_updates()
                    else:
                        logger.warning("MongoDB not connected, skipping content check")
                else:
                    logger.warning("No MongoDB credentials configured, skipping content check")
            else:
                logger.warning("Network is offline, skipping initial content check")
        except Exception as e:
            logger.error(f"Error during initial content check: {e}", exc_info=True)
        
    def stop(self):
        """Stop the cache manager background thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        logger.info("Cache Manager stopped")
            
    def _run(self):
        """Main loop checking for updates and managing cache"""
        last_check_time = datetime.now() - timedelta(hours=2)  # Force initial check
        
        while self.running:
            try:
                # Check if it's time to look for updates
                if (datetime.now() - last_check_time).total_seconds() >= self.CHECK_INTERVAL:
                    # Only check for updates if we're online and MongoDB credentials are configured
                    if (self.network_monitor.get_status() == NetworkStatus.ONLINE and 
                            self.mongodb_client.has_credentials()):
                        
                        # Connect to MongoDB if not already connected
                        if not self.mongodb_client.connected:
                            self.mongodb_client.connect()
                        
                        if self.mongodb_client.connected:
                            logger.info("Checking for new content to cache")
                            self._check_for_updates()
                            last_check_time = datetime.now()
                
                # Cleanup cache if it's too large
                self._cleanup_if_needed()
                
                # Sleep for a bit before checking again
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in cache manager background thread: {e}")
                time.sleep(300)  # Longer delay after error
    
    def _check_for_updates(self):
        """Check if there are updates available for the cached content."""
        self.logger.info("Checking for cache updates...")
        needs_db_sync = False # Flag to track if any updates were queued

        try:
            # Check current MongoDB connection
            mongo_client = MongoDBClient()
            connected = mongo_client.connected and mongo_client.initialized
            if not connected:
                self.logger.warning("MongoDB not connected, skipping cache update check")
                return
                
            self.logger.info("MongoDB connected, checking for new content...")
            
            user = UserOperations.get_current_user()
            if not user:
                self.logger.warning("No user found, skipping cache update check")
                return
                
            subjects = UserOperations.get_user_subjects()
            if not subjects:
                self.logger.warning("No subjects found for user, skipping cache update check")
                return
                
            # Process each subject
            for subject in subjects:
                subject_name = subject['name']
                self.logger.debug(f"Checking updates for subject: {subject_name} (ID: {subject['subject_id']})")
                
                levels = subject['levels']
                enabled_levels = {
                    'grade_7': levels.get('grade_7', False),
                    'o_level': levels.get('o_level', False),
                    'a_level': levels.get('a_level', False)
                }
                
                for level_key, enabled in enabled_levels.items():
                    if not enabled: continue
                        
                    mongo_level = self._convert_level_to_mongo_format(level_key)
                    last_update = self._get_subject_last_updated(subject_name, level_key)
                    
                    # Simplified check: Always queue if checking (or add back timestamp logic if needed)
                    # if last_update and (time.time() - last_update < 3600):
                    #     self.logger.debug(f"Subject {subject_name}/{level_key} recently updated, skipping")
                    #     continue
                        
                    self.logger.info(f"Queueing update check for {subject_name}/{level_key}")
                    # Assume _queue_questions_for_caching updates local JSONs for questions and answers
                    self._queue_questions_for_caching(subject_name, level_key, mongo_level) 
                    needs_db_sync = True # Mark that updates were processed, DB sync needed
            
            # --- ADDED DB SYNC CALL ---
            # After checking all subjects/levels and potentially updating local JSON files,
            # trigger the sync from local JSONs to the main database.
            if needs_db_sync:
                self.logger.info("Local cache files potentially updated, initiating sync to database...")
                self.sync_all_local_cache_to_db()
            else:
                 self.logger.info("No new content queued for local caching, skipping database sync.")
            # --- END ADDED DB SYNC CALL ---

        except Exception as e:
            self.logger.error(f"Error checking for updates: {e}", exc_info=True)
    
    def _verify_subscription(self) -> str:
        """
        Verify user subscription status
        
        Returns:
            str: Subscription status (SubscriptionStatus enum value)
        """
        # Check if we have cached subscription info that's still valid
        current_time = time.time()
        if (self.subscription_cache is not None and 
            current_time - self.subscription_cache_time < self.SUBSCRIPTION_CACHE_TTL):
            # Use cached value if it's fresh
            return self.subscription_cache
            
        try:
            # Import services here to avoid circular import
            from src.core import services
            
            # Get subscription status from Firebase
            subscription_data = services.firebase_client.check_subscription_status()
            
            # Debug the full document structure
            logger.debug(f"Full subscription data from Firebase: {subscription_data}")
            
            # CRITICAL FIX: The document might be in one of two formats:
            # 1. Direct Firestore format with fields at the top level
            # 2. Nested format with fields inside a 'fields' key
            
            # First, try to extract fields if they're in a nested structure
            if 'fields' in subscription_data:
                fields = subscription_data['fields']
            else:
                # If 'fields' key doesn't exist, assume the document itself contains the fields
                fields = subscription_data
                
            logger.debug(f"Extracted fields: {fields}")
            
            # Extract subscription type from fields
            subscription_type = None
            if 'subscribed' in fields:
                sub_field = fields['subscribed']
                # It could be a direct string value or nested in a stringValue field
                if isinstance(sub_field, dict) and 'stringValue' in sub_field:
                    subscription_type = sub_field['stringValue'].lower()
                elif isinstance(sub_field, str):
                    subscription_type = sub_field.lower()
            
            logger.info(f"Extracted subscription type: {subscription_type}")
            
            # Extract expiration date from fields
            sub_end_str = None
            if 'sub_end' in fields:
                end_field = fields['sub_end']
                # It could be a direct string value or nested in a stringValue field
                if isinstance(end_field, dict) and 'stringValue' in end_field:
                    sub_end_str = end_field['stringValue']
                elif isinstance(end_field, str):
                    sub_end_str = end_field
            
            logger.info(f"Extracted subscription end date: {sub_end_str}")
            
            # Determine subscription status
            current_date = datetime.now()
            
            # Check subscription type first
            if subscription_type not in self.VALID_SUBSCRIPTION_TYPES:
                logger.warning(f"Invalid subscription type: {subscription_type}")
                status = SubscriptionStatus.EXPIRED
            elif not sub_end_str:
                # No expiration date provided
                logger.warning("No subscription end date found in user data")
                # For trial subscriptions without end date, consider them active
                if subscription_type == "trial":
                    logger.info("Trial subscription without end date - considering active")
                    status = SubscriptionStatus.ACTIVE
                else:
                    status = SubscriptionStatus.EXPIRED
            else:
                # Parse expiration date
                try:
                    sub_end_date = datetime.fromisoformat(sub_end_str)
                    
                    # Check if expired
                    if current_date > sub_end_date:
                        logger.warning(f"Subscription expired on {sub_end_date.isoformat()}")
                        status = SubscriptionStatus.EXPIRED
                    else:
                        # Check if nearing expiration
                        warning_date = sub_end_date - timedelta(days=self.SUBSCRIPTION_WARNING_DAYS)
                        if current_date >= warning_date:
                            status = SubscriptionStatus.EXPIRING
                            days_left = (sub_end_date - current_date).days
                            logger.info(f"Subscription expiring soon! {days_left} days remaining")
                            self._show_expiration_warning(sub_end_date)
                        else:
                            status = SubscriptionStatus.ACTIVE
                            logger.info(f"Subscription is active until {sub_end_date.isoformat()}")
                except ValueError as e:
                    logger.error(f"Invalid date format for subscription end: {sub_end_str} - {e}")
                    status = SubscriptionStatus.EXPIRED
            
            # Show expiration alert if applicable
            if status == SubscriptionStatus.EXPIRED:
                self._show_expiration_alert()
            
            # Cache the result
            self.subscription_cache = status
            self.subscription_cache_time = current_time
            
            return status
            
        except Exception as e:
            logger.error(f"Error verifying subscription: {e}")
            
            # For exceptions during verification, allow content access
            # (better user experience to show content than to block incorrectly)
            return SubscriptionStatus.ACTIVE
    
    def _show_expiration_warning(self, expiration_date: datetime):
        """Display a warning that subscription will expire soon"""
        days_left = (expiration_date - datetime.now()).days
        message = f"Your subscription will expire in {days_left} days. Please renew to maintain access."
        logger.warning(message)
        
        # Here you could trigger a UI notification if appropriate
    
    def _show_expiration_alert(self):
        """Display an alert that subscription has expired"""
        message = "Your subscription has expired. You can only access previously cached content."
        logger.warning(message)
        
        # Here you could trigger a UI notification if appropriate
    
    def is_subscribed(self) -> bool:
        """
        Check if user has an active subscription
        
        Returns:
            bool: True if subscription is active or expiring soon
        """
        status = self._verify_subscription()
        return status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.EXPIRING]
    
    def get_subscription_info(self) -> Dict[str, Any]:
        """
        Get detailed subscription information
            
        Returns:
            Dict containing subscription status and details
        """
        try:
            # Get subscription status from Firebase
            firebase = FirebaseClient()
            subscription_data = firebase.check_subscription_status()
            
            # Get key fields
            subscription_type = subscription_data.get('subscribed', '').lower()
            sub_end_str = subscription_data.get('sub_end', '')
            
            # Parse expiration date
            try:
                if sub_end_str:
                    sub_end_date = datetime.fromisoformat(sub_end_str)
                    days_remaining = (sub_end_date - datetime.now()).days
                else:
                    sub_end_date = None
                    days_remaining = None
            except ValueError:
                logger.error(f"Invalid date format for subscription end: {sub_end_str}")
                sub_end_date = None
                days_remaining = None
            
            # Get status
            status = self._verify_subscription()
            
            return {
                "status": status,
                "type": subscription_type,
                "end_date": sub_end_date.isoformat() if sub_end_date else None,
                "days_remaining": days_remaining,
                "is_active": status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.EXPIRING]
            }
            
        except Exception as e:
            logger.error(f"Error getting subscription info: {e}")
            return {
                "status": SubscriptionStatus.ACTIVE,  # Default to active on error
                "type": "unknown",
                "end_date": None,
                "days_remaining": None,
                "is_active": True,
                "error": str(e)
            }
    
    def _convert_level_to_mongo_format(self, level_key: str) -> str:
        """Convert internal level key to MongoDB level format"""
        level_mapping = {
            'grade_7': 'primary school',  # MongoDB uses lowercase for questions
            'o_level': 'olevel',           # MongoDB uses lowercase for questions 
            'a_level': 'aslevel'           # MongoDB uses lowercase for questions
        }
        logger.debug(f"Converting UI level '{level_key}' to MongoDB format: '{level_mapping.get(level_key, level_key)}'")
        return level_mapping.get(level_key, level_key)
    
    def _get_cached_question_count(self, subject: str, level: str) -> int:
        """Get count of cached questions for a subject and level"""
        try:
            # Query the questions directory for matching files
            subject_dir = os.path.join(self.QUESTIONS_DIR, self._safe_filename(subject), level)
            
            if not os.path.exists(subject_dir):
                return 0
                
            # Count question files
            count = 0
            for root, dirs, files in os.walk(subject_dir):
                count += len([f for f in files if f.endswith('.json')])
                
            return count
            
        except Exception as e:
            logger.error(f"Error counting cached questions: {e}")
            return 0
    
    def _extract_question_number(self, question: Dict) -> Optional[str]:
        """
        Extract question number from question document
        
        Args:
            question: Question document
            
        Returns:
            Question number as string, or None if not found
        """
        try:
            # Use a unique identifier if no question number is available
            # This ensures we don't skip questions just because they don't have a standard question number
            doc_id = str(question.get('_id', ''))
            if doc_id:
                # Use a shortened version of the document ID as a fallback question number
                fallback_number = doc_id[-6:]  # Last 6 chars of the ID
            else:
                fallback_number = str(uuid.uuid4())[-6:]  # Random ID if no document ID
            
            # Try to extract from various possible locations
            # 1. Direct field access
            for field in ['question_number', 'QuestionNumber', 'Number', 'Question_Number', 'number']:
                if field in question:
                    value = question[field]
                    # Handle MongoDB extended JSON format
                    if isinstance(value, dict) and '$numberInt' in value:
                        return str(value['$numberInt'])
                    return str(value)
            
            # 2. Check if question number is in 'paper_meta'
            if 'paper_meta' in question:
                paper_meta = question['paper_meta']
                for field in ['QuestionNumber', 'Number', 'question_number']:
                    if field in paper_meta:
                        return str(paper_meta[field])
            
            # 3. Check in 'questions' array
            if 'questions' in question and isinstance(question['questions'], list):
                for q in question['questions']:
                    if 'question_number' in q:
                        return str(q['question_number'])
            
            # 4. Generate from other metadata if available
            if 'paper_meta' in question:
                paper_meta = question['paper_meta']
                if 'Year' in paper_meta and 'PaperNumber' in paper_meta:
                    return f"{paper_meta['Year']}_{paper_meta['PaperNumber']}"
            
            # Return the fallback identifier
            logger.info(f"Using fallback question number {fallback_number} for document {doc_id}")
            return fallback_number
            
        except Exception as e:
            logger.error(f"Error extracting question number: {e}")
            return None
    
    def _mongo_to_json_serializable(self, obj):
        """Convert MongoDB document with special types to JSON-serializable dict"""
        if isinstance(obj, dict):
            # Convert all dict keys/values
            return {k: self._mongo_to_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            # Convert all list items
            return [self._mongo_to_json_serializable(item) for item in obj]
        elif str(type(obj)) == "<class 'bson.objectid.ObjectId'>":
            # Convert ObjectId to string
            return str(obj)
        elif isinstance(obj, (datetime, date)):
            # Convert datetime objects to ISO format strings
            return obj.isoformat()
        else:
            # Return other types as is
            return obj
            
    def _get_int_q_num(self, item: dict, key: str = 'question_number') -> Optional[int]:
        """
        Safely extracts an integer question number from a dictionary.
        Handles integers, strings, $numberInt, floats, and strings with whitespace.
        """
        q_num_raw = item.get(key)
        self.logger.debug(f"[_get_int_q_num] Raw value for key '{key}': {q_num_raw} (type: {type(q_num_raw)})")

        if q_num_raw is None:
            self.logger.debug(f"[_get_int_q_num] Raw value is None.")
            return None

        # 1. Check if already an integer
        if isinstance(q_num_raw, int):
            self.logger.debug(f"[_get_int_q_num] Raw value is already int: {q_num_raw}")
            return q_num_raw

        # 2. Check for MongoDB $numberInt format
        if isinstance(q_num_raw, dict) and '$numberInt' in q_num_raw:
            try:
                val = int(q_num_raw['$numberInt'])
                self.logger.debug(f"[_get_int_q_num] Extracted int from $numberInt: {val}")
                return val
            except (ValueError, TypeError):
                self.logger.warning(f"[_get_int_q_num] Invalid $numberInt format: {q_num_raw}")
                # Continue trying other formats below
                pass # Don't return None yet

        # 3. Check if it's a float (that can be cleanly converted to int)
        if isinstance(q_num_raw, float):
            if q_num_raw.is_integer():
                try:
                    val = int(q_num_raw)
                    self.logger.debug(f"[_get_int_q_num] Converted float to int: {val}")
                    return val
                except (ValueError, TypeError):
                     self.logger.warning(f"[_get_int_q_num] Could not convert float {q_num_raw} to int.")
                     # Continue trying other formats
                     pass
            else:
                self.logger.warning(f"[_get_int_q_num] Float value {q_num_raw} is not a whole number, cannot convert cleanly to int.")
                 # Continue trying other formats
                pass

        # 4. Check if it's a string (attempt to convert after stripping whitespace)
        if isinstance(q_num_raw, str):
            stripped_val = q_num_raw.strip()
            if not stripped_val: # Handle empty strings after stripping
                 self.logger.warning(f"[_get_int_q_num] String value '{q_num_raw}' is empty after stripping.")
                 return None
            try:
                # First, try converting directly to int
                val = int(stripped_val)
                self.logger.debug(f"[_get_int_q_num] Converted stripped string to int: {val}")
                return val
            except ValueError:
                 # If direct int fails, try converting as float first, then to int
                 try:
                      float_val = float(stripped_val)
                      if float_val.is_integer():
                           int_val = int(float_val)
                           self.logger.debug(f"[_get_int_q_num] Converted stripped string->float->int: {int_val}")
                           return int_val
                      else:
                           self.logger.warning(f"[_get_int_q_num] String '{stripped_val}' represents a non-integer float.")
                           return None
                 except ValueError:
                      self.logger.warning(f"[_get_int_q_num] Could not convert string '{stripped_val}' to int or float.")
                      return None

        # If none of the above worked
        self.logger.warning(f"[_get_int_q_num] Unhandled type or format for question number '{key}': {q_num_raw} (type: {type(q_num_raw)})")
        return None

    def _queue_questions_for_caching(self, subject: str, level_key: str, mongo_level: str):
        """
        Queue questions for the specified subject and level for caching.
        Finds the single matching answer document per question document using consolidated logic.
        """
        self.logger.info(f"Queueing questions for caching: {subject} at {level_key} (MongoDB level: {mongo_level})")
        processed_papers_metadata = []

        try:
            client = MongoDBClient() # Get current instance
            # ... (Connection check) ...

            # 1. Fetch the Question Paper documents (Still fetches multiple initially)
            question_documents = client.get_questions_by_subject_level(subject, mongo_level, limit=50)
            self.logger.info(f"Found {len(question_documents)} source question paper documents to process for {subject} at {level_key}")

            if not question_documents:
                # ... (handle no documents found) ...
                return

            # *** Define the target IDs we actually want to fully process ***
            # You might get these from config, user settings, or hardcode them if static
            target_paper_ids_str = {
                "67d50ebecec12312c07d55f9", # 2022 Paper
                "67d50f56da1cae21c770da4d"  # 2024 Paper
            }
            target_paper_object_ids = {ObjectId(id_str) for id_str in target_paper_ids_str}
            self.logger.info(f"Will perform full processing only for target _ids: {target_paper_ids_str}")


            # Create base cache directories
            # ... (directory creation logic) ...
            safe_subject = self._safe_filename(subject)
            safe_level = self._safe_filename(level_key)
            questions_base_dir = os.path.join(self.QUESTIONS_DIR, safe_subject, safe_level)
            answers_base_dir = os.path.join(self.ANSWERS_DIR, safe_subject, safe_level)
            os.makedirs(questions_base_dir, exist_ok=True)
            os.makedirs(answers_base_dir, exist_ok=True)


            # 2. Process each source Question Paper document
            for doc_index, question_doc_raw in enumerate(question_documents):
                # --- Initialize counters for THIS paper ---
                doc_question_count = 0
                doc_answer_count = 0
                doc_valid_image_url_count = 0
                doc_downloaded_image_count = 0
                matching_answer_doc_for_this_paper = None
                # --- End Initialize counters ---


                # Extract the primary _id from the raw question doc
                mongo_question_object_id = question_doc_raw.get('_id')
                if not mongo_question_object_id or not isinstance(mongo_question_object_id, ObjectId):
                     self.logger.error(f"Could not extract valid ObjectId from question document index {doc_index}. Skipping.")
                     continue

                safe_question_doc = self._mongo_to_json_serializable(question_doc_raw)
                mongo_question_doc_id_str = str(mongo_question_object_id)

                self.logger.info(f"--- Processing Question Paper #{doc_index + 1}/{len(question_documents)} with _id: {mongo_question_object_id} ---")

                # Extract Metadata
                source_document_id = safe_question_doc.get('document_id') 
                source_file_id = safe_question_doc.get('file_id')
                source_file_name = safe_question_doc.get('file_name')
                paper_meta = safe_question_doc.get('paper_meta', {})
                year = str(paper_meta.get('Year', 'Unknown'))
                term = str(paper_meta.get('Term', 'Unknown'))
                paper_number = str(paper_meta.get('Paper', 'Unknown'))

                year_questions_dir = os.path.join(questions_base_dir, year) 
                year_answers_dir = os.path.join(answers_base_dir, year)   
                os.makedirs(year_questions_dir, exist_ok=True)
                os.makedirs(year_answers_dir, exist_ok=True)

                # Check if this paper should be a target based on criteria
                # (Assuming is_target_paper logic exists or is determined here)
                is_target_paper = True # Example: Assume we process all for now

                # 3. Process and save each Question within the Paper
                if 'questions' in safe_question_doc and isinstance(safe_question_doc['questions'], list):
                    for question_index, question_item in enumerate(safe_question_doc['questions']):
                        if not isinstance(question_item, dict): 
                            self.logger.warning(f"Skipping question item at index {question_index} in paper {mongo_question_doc_id_str} because it's not a dictionary.")
                            continue
                        
                        q_num_int = self._get_int_q_num(question_item)
                        # Use index as fallback ONLY if integer conversion fails
                        question_number_str = str(q_num_int) if q_num_int is not None else f"idx{question_index}"
                        self.logger.debug(f"Processing Q {question_number_str} from paper {mongo_question_doc_id_str}")

                        # --- Process Images for this question ---
                        processed_images = []
                        original_images = question_item.get('images', [])
                        if isinstance(original_images, list):
                            for img_idx, img_data in enumerate(original_images):
                                if isinstance(img_data, dict):
                                    url = img_data.get('url')
                                    label = img_data.get('label')
                                    description = img_data.get('description')
                                    
                                    if url: # Only process if there is a URL
                                        doc_valid_image_url_count += 1 # Increment valid URL count here
                                        self.logger.debug(f"Attempting download for Q {question_number_str}, Img {img_idx}, URL: {url}")
                                        # Attempt to download the asset
                                        local_path = self._download_and_save_asset(
                                            url=url,
                                            subject=subject,
                                            level=level_key, # Use level_key consistently
                                            year=year,
                                            question_number=question_number_str, 
                                            image_index=img_idx,
                                            image_label=label 
                                        )
                                        
                                        # Create the image entry for the JSON cache
                                        processed_image_entry = {
                                            "label": label,
                                            "description": description,
                                            "url": url, # Keep original URL 
                                            "local_path": local_path # Will be None if download failed
                                        }
                                        processed_images.append(processed_image_entry)
                                        
                                        if local_path: 
                                            self.logger.info(f"Successfully downloaded and got path for Q {question_number_str}, Img {img_idx}: {local_path}")
                                            doc_downloaded_image_count += 1 # Increment download count ONLY if successful
                                        else:
                                             self.logger.warning(f"Download failed for Q {question_number_str}, Img {img_idx}, URL: {url}")
                                    else:
                                        self.logger.warning(f"Skipping image processing for Q {question_number_str}, Img {img_idx}: Missing URL.")
                                else:
                                     self.logger.warning(f"Skipping invalid image data entry (not a dict) in Q {question_number_str}, index {img_idx}")
                        else:
                             self.logger.warning(f"Images data for Q {question_number_str} is not a list, skipping image processing.")
                        # --- End Process Images ---

                        # --- Prepare and Save Question JSON ---
                        question_data_to_save = {
                            "id": mongo_question_doc_id_str, "subject": subject, "level": level_key, "year": year,
                            "question_number_str": question_number_str,
                            "question_text": question_item.get("question_text", ""), 
                            "topic": question_item.get("topic"),
                            "subtopic": question_item.get("subtopic"), 
                            "difficulty": question_item.get("difficulty"),
                            "context_materials": question_item.get("context_materials"), 
                            "sub_questions": question_item.get("sub_questions"),
                            "tables": question_item.get("tables"), 
                            "marks": question_item.get("marks"),
                            "images": processed_images, # Use the potentially populated list
                            "answer_ref": f"{question_number_str}.json" # Ensure answer ref matches question number
                        }
                        
                        # Construct filename using the determined question_number_str
                        question_filename = os.path.join(year_questions_dir, f"{question_number_str}.json")
                        self.logger.debug(f"Attempting to save question data to: {question_filename}")
                        try:
                            with open(question_filename, 'w', encoding='utf-8') as f: 
                                json.dump(question_data_to_save, f, ensure_ascii=False, indent=4)
                            self.logger.info(f"Successfully saved question file: {question_filename}")
                            doc_question_count += 1 # Increment only on successful save
                        except Exception as e: 
                            self.logger.error(f"Failed to save question file {question_filename}: {e}", exc_info=True)
                        # --- End Save Question JSON ---

                    # ...(rest of the loop for processing answers for this paper)...

                else:
                     self.logger.warning(f"Paper {mongo_question_doc_id_str} has no 'questions' list or it's not a list.")

                # --- Find and process matching answer doc (IF this paper was a target) ---
                # Reset answer count for this paper before processing answers
                doc_answer_count = 0 
                if is_target_paper:
                    # ... (Existing logic for finding and processing matching_answer_doc_for_this_paper) ...
                    # Make sure to increment doc_answer_count inside the answer saving logic if it succeeds
                    pass # Placeholder for answer processing logic


                # --- Store metadata for this paper (AFTER processing questions AND answers) ---
                paper_metadata = {
                    "mongo_doc_id": mongo_question_doc_id_str,
                    "source_document_id": source_document_id, "source_file_id": source_file_id,
                    "source_file_name": source_file_name, "year": year, "term": term, "paper_number": paper_number,
                    "question_count": doc_question_count,
                    "answer_count_cached": doc_answer_count, 
                    "image_url_count": doc_valid_image_url_count, 
                    "image_download_count": doc_downloaded_image_count,
                    "is_target_paper": is_target_paper, 
                    "answer_doc_found_by": "..." # Fill this based on answer lookup result
                }
                processed_papers_metadata.append(paper_metadata)
                self.logger.debug(f"Collected metadata for paper {mongo_question_doc_id_str}: Questions={doc_question_count}, Answers={doc_answer_count}, ImgURLs={doc_valid_image_url_count}, ImgDLs={doc_downloaded_image_count}")


            # --- After processing all documents for this subject/level ---
            # ... (Update global metadata using processed_papers_metadata) ...

        except Exception as e:
            self.logger.error(f"Error in _queue_questions_for_caching for {subject}/{level_key}: {e}", exc_info=True)

    def _download_and_save_asset(self, url: str, subject: str, level: str, year: str, question_number: str, image_index: int, image_label: Optional[str] = None) -> Optional[str]:
        """
        Downloads an image asset, handling HTML pages from imgbb, saves it locally,
        and returns the relative path.
        """
        self.logger.debug(f"_download_and_save_asset called for q#{question_number}, img#{image_index}, label='{image_label}', url='{url}'")
        if not url or not isinstance(url, str) or not url.startswith(('http://', 'https://')):
            self.logger.warning(f"Skipping download for q#{question_number}, img#{image_index}: Invalid or missing URL: {url}")
            return None

        local_asset_path_full = None
        relative_asset_path = None
        session = requests.Session()
        headers = {
             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        try:
            # Step 1: Fetch initial content
            self.logger.info(f"Fetching initial content for q#{question_number}, img#{image_index} from URL: {url}")
            response1 = session.get(url, headers=headers, timeout=20, allow_redirects=True)
            self.logger.debug(f"Initial request status code: {response1.status_code}")
            response1.raise_for_status()
            content_type1 = response1.headers.get('content-type', '').lower()
            self.logger.info(f"Initial Content-Type: {content_type1} for URL: {url}")

            image_content = None

            # Step 2 & 3: Check if HTML, Parse, Find & Fetch Direct Image URL
            if 'text/html' in content_type1:
                self.logger.info(f"Content is HTML. Parsing to find direct image link for {url}...")
                try:
                    soup = BeautifulSoup(response1.text, 'lxml')
                    # --- Find the main image element (VERIFY THESE SELECTORS for imgbb) ---
                    img_tag = soup.find('img', {'id': 'image-viewer-image'})
                    if not img_tag: img_tag = soup.select_one('div.image-viewer img') # Adjust selector if needed
                    if not img_tag: img_tag = soup.find('img', src=re.compile(r'//i\.ibb\.co/')) # Find img with i.ibb.co source (note: // start)
                    # --- End Finding Element ---

                    if img_tag and img_tag.get('src'):
                        direct_image_url = img_tag['src']
                        # Handle protocol-relative URLs (like //i.ibb.co/...)
                        if direct_image_url.startswith('//'):
                             direct_image_url = 'https:' + direct_image_url
                        self.logger.info(f"Extracted potential direct image URL: {direct_image_url}")

                        # --- Step 4: Fetch the *Real* Image ---
                        self.logger.info(f"Fetching actual image content from: {direct_image_url}")
                        response2 = session.get(direct_image_url, headers=headers, stream=True, timeout=20)
                        content_type2 = response2.headers.get('content-type', '').lower()
                        self.logger.info(f"SECOND request status: {response2.status_code}, Content-Type: {content_type2}")
                        response2.raise_for_status()

                        if 'image/' in content_type2:
                            image_content = response2.content
                            self.logger.info(f"Successfully obtained image bytes ({len(image_content)} bytes) from second request.")
                        else:
                            self.logger.error(f"Second request to {direct_image_url} did not yield image content (type: {content_type2}). Skipping save.")
                            return None
                    else:
                        self.logger.error(f"Could not find valid 'src' attribute in located img tag OR could not find tag itself in HTML from {url}. Skipping save.")
                        return None
                except Exception as parse_err:
                     self.logger.error(f"Error during BeautifulSoup parsing for {url}: {parse_err}", exc_info=True)
                     return None
            elif 'image/' in content_type1:
                 self.logger.info(f"Initial content from {url} is already an image ({content_type1}). Using directly.")
                 image_content = response1.content
            else:
                self.logger.warning(f"Content from {url} is neither HTML nor a recognized image type ({content_type1}). Skipping.")
                return None

            # --- Path and Filename Construction ---
            safe_subject = self._safe_filename(subject)
            safe_level = self._safe_filename(level)
            asset_sub_dir = os.path.join(self.ASSETS_DIR, safe_subject, safe_level, str(year))
            os.makedirs(asset_sub_dir, exist_ok=True)

            final_content_type = response2.headers.get('content-type', content_type1) if 'response2' in locals() else content_type1
            extension = mimetypes.guess_extension(final_content_type) if final_content_type else '.png'
            if not extension or extension == '.jpe': extension = '.jpg'

            label_part = self._safe_filename(image_label) if image_label else f"img_{image_index}"
            # Ensure question_number is a string for filename
            asset_filename = f"q{str(question_number)}_{label_part}{extension}" 
            local_asset_path_full = os.path.join(asset_sub_dir, asset_filename)
            # Construct relative path assuming ASSETS_DIR is like "src/data/cache/assets"
            relative_asset_path = os.path.join(self.ASSETS_DIR, safe_subject, safe_level, str(year), asset_filename)
            self.logger.debug(f"Determined save path: {local_asset_path_full}")

            # --- Step 5: Save Correct Image Bytes ---
            if isinstance(image_content, bytes):
                 # This block executes if image_content has valid bytes
                 self.logger.info(f"Saving actual image content ({len(image_content)} bytes) to: {local_asset_path_full}")
                 try:
                      with open(local_asset_path_full, 'wb') as f:
                          f.write(image_content)
                      self.logger.info(f"Successfully saved file: {local_asset_path_full}")
                 except IOError as write_err:
                      self.logger.error(f"IOError saving image file {local_asset_path_full}: {write_err}")
                      return None # Return None if saving fails
            else: # <--- This 'else' now aligns with the 'if' on line 884
                 # This block executes if image_content was None or not bytes
                 self.logger.error(f"Image content for {local_asset_path_full} was not in bytes format or download failed. Cannot save.")
                 return None # Return None if no valid bytes to save

            # If saving was successful (we didn't return None from either block above)
            self.logger.debug(f"Returning relative path: {relative_asset_path}")
            return relative_asset_path

        except requests.exceptions.Timeout:
             self.logger.error(f"Timeout error during image processing for q#{question_number}, img#{image_index} (Initial URL: {url})")
             return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error during image processing for q#{question_number}, img#{image_index} (Initial URL: {url}): {e}")
            return None
        except IOError as e:
             self.logger.error(f"File saving error for q#{question_number}, img#{image_index} to {local_asset_path_full}: {e}")
             # Attempt cleanup?
             return None
        except ImportError:
             self.logger.critical("BeautifulSoup or lxml not installed. Cannot parse HTML to find images.")
             return None
        except Exception as e:
            self.logger.error(f"Unexpected error processing image for q#{question_number}, img#{image_index} (Initial URL: {url}): {e}", exc_info=True)
            return None

    def _update_global_subject_metadata(self, subject: str, level_key: str, processed_papers: List[Dict]):
        """
        Updates the global subjects.json metadata file.
        Handles potential JSONDecodeError when reading existing file.
        Corrects indentation for file writing exception handling.

        Args:
            subject: The subject being updated.
            level_key: The level being updated.
            processed_papers: A list of dictionaries, each containing metadata for a paper processed in the current run.
        """
        metadata_file = os.path.join(self.METADATA_DIR, "subjects.json")
        self.logger.debug(f"Updating global metadata file: {metadata_file} for {subject}/{level_key}")

        with self.global_metadata_lock: # Acquire lock for file access
            all_metadata = {} # Default to empty dict
            try: # Try reading the file
                os.makedirs(self.METADATA_DIR, exist_ok=True)
                if os.path.exists(metadata_file):
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        try:
                            all_metadata = json.load(f)
                            if not isinstance(all_metadata, dict):
                                 self.logger.warning(f"Global metadata file {metadata_file} did not contain a valid JSON object. Starting fresh.")
                                 all_metadata = {}
                        except json.JSONDecodeError:
                            self.logger.warning(f"Could not decode existing global metadata file: {metadata_file}. File might be empty or corrupted. Starting fresh.")
                            all_metadata = {}
            except Exception as e: # Catch errors during reading/checking file
                 self.logger.error(f"Error reading global metadata file {metadata_file}: {e}. Starting fresh.")
                 all_metadata = {}

            # --- Proceed with updating the metadata structure ---
            subject_metadata = all_metadata.setdefault(subject, {})
            level_metadata = subject_metadata.setdefault(level_key, {"papers": []})
            level_metadata['last_checked_timestamp'] = time.time()
            level_metadata['papers'] = processed_papers
            level_metadata['total_papers_processed_last_run'] = len(processed_papers)
            level_metadata['total_questions_processed_last_run'] = sum(p.get('question_count', 0) for p in processed_papers)
            level_metadata['total_images_downloaded_last_run'] = sum(p.get('image_download_count', 0) for p in processed_papers)

            # --- Write updated data back ---
            try: # Inner try specifically for writing
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(all_metadata, f, indent=2)
                self.logger.info(f"Successfully updated global metadata for {subject}/{level_key}")
            # --- FIX: Correctly indented except block for the write 'try' ---
            except Exception as e:
                 self.logger.error(f"Failed to write global metadata file {metadata_file}: {e}", exc_info=True)
            # --- END FIX ---
            
    def get_cached_question(self, subject: str, level: str, year: str = None, 
                           question_number: str = None, random: bool = False) -> Optional[Dict]:
        """
        Get a cached question from local storage.
        
        Args:
            subject: Subject name
            level: Level key
            year: Optional year filter
            question_number: Optional question number filter
            random: If True, return a random question matching criteria
            
        Returns:
            Question data or None if not found
        """
        # Check subscription status but don't block access to already cached content
        is_active = self.is_subscribed()
        
        try:
            # Create subject path
            subject_path = os.path.join(self.QUESTIONS_DIR, self._safe_filename(subject), level)
            
            if not os.path.exists(subject_path):
                return None
                
            # Get all question files matching criteria
            matching_files = []
            
            # If year is specified, look in that year directory
            if year:
                year_path = os.path.join(subject_path, year)
                if os.path.exists(year_path):
                    for filename in os.listdir(year_path):
                        if filename.endswith('.json'):
                            # If question number is specified, match it
                            if question_number and f"_q{question_number}" not in filename:
                                continue
                            matching_files.append(os.path.join(year_path, filename))
            else:
                # Search all years
                for root, dirs, files in os.walk(subject_path):
                    for filename in files:
                        if filename.endswith('.json'):
                            # If question number is specified, match it
                            if question_number and f"_q{question_number}" not in filename:
                                continue
                            matching_files.append(os.path.join(root, filename))
            
            if not matching_files:
                return None
                
            # Select file (random or first)
            selected_file = random.choice(matching_files) if random else matching_files[0]
            
            # Load question data
            with open(selected_file, 'r', encoding='utf-8') as f:
                question_data = json.load(f)
                
            # Resolve asset paths
            self._resolve_asset_paths(question_data)
                
            # If we found content but subscription is expired, add warning
            if not is_active:
                question_data['subscription_expired'] = True
                
            return question_data
            
        except Exception as e:
            logger.error(f"Error getting cached question: {e}")
            return None
    
    def get_cached_questions_for_test(self, subject: str, level: str, count: int = 10) -> List[Dict]:
        """
        Get a set of questions suitable for a test.
        
        Args:
            subject: Subject name
            level: Level key
            count: Number of questions to return
            
        Returns:
            List of question data
        """
        questions = []
        try:
            # Get recent years first
            years = self._get_available_years(subject, level)
            years.sort(reverse=True)  # Most recent first
            
            questions_needed = count
            
            # Try to get an even distribution across years
            for year in years:
                # Calculate how many questions to get from this year
                year_count = min(questions_needed, count // len(years) + 1)
                
                # Get questions from this year
                year_questions = self._get_questions_from_year(subject, level, year, year_count)
                questions.extend(year_questions)
                
                questions_needed -= len(year_questions)
                if questions_needed <= 0:
                    break
            
            # If we still need more questions, get random ones
            while len(questions) < count and questions_needed > 0:
                q = self.get_cached_question(subject, level, random=True)
                if q and q not in questions:
                    questions.append(q)
                    questions_needed -= 1
                else:
                    # Avoid infinite loop if we can't find more questions
                    break
                    
            return questions
            
        except Exception as e:
            logger.error(f"Error getting questions for test: {e}")
            return questions
    
    def _get_available_years(self, subject: str, level: str) -> List[str]:
        """Get list of years that have cached questions for the subject/level"""
        years = []
        try:
            subject_path = os.path.join(self.QUESTIONS_DIR, self._safe_filename(subject), level)
            
            if not os.path.exists(subject_path):
                return []
    
            # List directories in the subject path - these are years
            for item in os.listdir(subject_path):
                if os.path.isdir(os.path.join(subject_path, item)):
                    years.append(item)
                    
            return years
            
        except Exception as e:
            logger.error(f"Error getting available years: {e}")
            return []
    
    def _get_questions_from_year(self, subject: str, level: str, year: str, count: int) -> List[Dict]:
        """Get a specific number of questions from a particular year"""
        questions = []
        try:
            year_path = os.path.join(self.QUESTIONS_DIR, self._safe_filename(subject), level, year)
            if not os.path.exists(year_path):
                logger.warning(f"Path does not exist: {year_path}")
                return []
                
            # Get all question files for this year
            question_files = [f for f in os.listdir(year_path) if f.endswith('.json')]
            
            if not question_files:
                logger.warning(f"No question files found in {year_path}")
                return []
                
            # Random selection if we need a subset
            if count < len(question_files):
                selected_files = random.sample(question_files, count)
            else:
                selected_files = question_files
                
            # Load selected questions
            for qfile in selected_files:
                file_path = os.path.join(year_path, qfile)
                try:
                    with open(file_path, 'r') as f:
                        question_data = json.load(f)
                        # Resolve asset paths
                        self._resolve_asset_paths(question_data)
                        questions.append(question_data)
                except Exception as e:
                    logger.error(f"Error loading question {file_path}: {e}")
                    
            return questions
        except Exception as e:
            logger.error(f"Error getting questions from year {year}: {e}")
            return []
    
    def _resolve_asset_paths(self, question_data: Dict):
        """
        Update image URLs in question data to point to local files.
        Modifies question_data in place.
        """
        try:
            subject = question_data.get('subject')
            level = question_data.get('level')
            year = question_data.get('year')
            question_number = question_data.get('question_number')
            
            if not all([subject, level, year, question_number]):
                return
                
            # Path to asset directory for this question
            asset_dir = os.path.join(
                self.ASSETS_DIR, 
                self._safe_filename(subject), 
                level, 
                year, 
                str(question_number)
            )
            
            if not os.path.exists(asset_dir):
                return
                
            # Get question data
            q_data = question_data.get('data', {})
            
            # Update image paths
            images = q_data.get('images', [])
            for idx, img_data in enumerate(images):
                img_url = img_data.get('url')
                if not img_url:
                    continue
                    
                # Generate the expected filename
                filename = f"image_{idx}_{self._hash_url(img_url)}.jpg"
                filepath = os.path.join(asset_dir, filename)
                
                if os.path.exists(filepath):
                    # Update URL to local file
                    img_data['original_url'] = img_url
                    img_data['url'] = f"file://{filepath}"
                    
        except Exception as e:
            logger.error(f"Error resolving asset paths: {e}")
    
    def _cleanup_if_needed(self):
        """Check if cache is too large and clean up if necessary"""
        try:
            # Get current cache size
            cache_size = self._get_cache_size_mb()
            
            if cache_size > self.MAX_CACHE_SIZE_MB:
                logger.info(f"Cache size ({cache_size}MB) exceeds limit ({self.MAX_CACHE_SIZE_MB}MB). Cleaning up...")
                self._cleanup_cache()
                
        except Exception as e:
            logger.error(f"Error checking cache size: {e}")
    
    def _get_cache_size_mb(self) -> float:
        """Get the current size of the cache in MB"""
        total_size = 0
        
        # Add size of questions directory
        total_size += self._get_directory_size(self.QUESTIONS_DIR)
        
        # Add size of assets directory
        total_size += self._get_directory_size(self.ASSETS_DIR)
        
        # Convert bytes to MB
        return total_size / (1024 * 1024)
    
    def _get_directory_size(self, path: str) -> int:
        """Get the size of a directory in bytes"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
                
        return total_size
    
    def _cleanup_cache(self):
        """Remove oldest/least used cached content to free up space"""
        try:
            # Get list of subjects
            subjects = os.listdir(self.QUESTIONS_DIR)
            
            # For each subject, remove oldest years first
            for subject in subjects:
                subject_path = os.path.join(self.QUESTIONS_DIR, subject)
                
                # Skip if not a directory
                if not os.path.isdir(subject_path):
                    continue
                    
                # For each level, get years
                for level in os.listdir(subject_path):
                    level_path = os.path.join(subject_path, level)
                    
                    # Skip if not a directory
                    if not os.path.isdir(level_path):
                        continue
                        
                    # Get years sorted oldest first
                    years = sorted(
                        [y for y in os.listdir(level_path) if os.path.isdir(os.path.join(level_path, y))],
                        key=lambda y: y if y.isdigit() else "0"
                    )
                    
                    # Keep removing oldest years until we're under the limit
                    while years and self._get_cache_size_mb() > self.MAX_CACHE_SIZE_MB * 0.8:
                        oldest_year = years.pop(0)
                        year_path = os.path.join(level_path, oldest_year)
                        
                        # Remove corresponding assets
                        asset_year_path = os.path.join(
                            self.ASSETS_DIR, subject, level, oldest_year
                        )
                        
                        # Remove question files
                        self._remove_directory(year_path)
                        
                        # Remove asset files
                        if os.path.exists(asset_year_path):
                            self._remove_directory(asset_year_path)
                            
                        logger.info(f"Removed cached content for {subject} {level} year {oldest_year}")
                        
                        # Break if we've cleaned up enough
                        if self._get_cache_size_mb() <= self.MAX_CACHE_SIZE_MB * 0.8:
                            break
            
        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
    
    def _remove_directory(self, path: str):
        """Safely remove a directory and all its contents"""
        try:
            import shutil
            if os.path.exists(path):
                shutil.rmtree(path)
        except Exception as e:
            logger.error(f"Error removing directory {path}: {e}")
    
    def _safe_filename(self, name: str) -> str:
        """Convert a string to a safe filename"""
        return "".join([c for c in name if c.isalnum() or c in (' ', '_')]).rstrip().replace(' ', '_').lower()
    
    def _hash_url(self, url: str) -> str:
        """Create a short hash of a URL for filename generation"""
        return hashlib.md5(url.encode()).hexdigest()[:10]
    
    def _ensure_tables(self):
        """Ensure required database tables exist"""
        pass  # We're using our own file-based storage, so no tables needed

    # Legacy methods for backward compatibility
    def mark_paper_completed(self, user_subject_id: int, year: int) -> bool:
        """Mark a paper as completed by the user (legacy method)"""
        return True  # No-op since we're not using this mechanism anymore
        
    def force_cache_check(self, user_id: int) -> Dict:
        """Force a check for cache updates (legacy method)"""
        if self.network_monitor.get_status() == NetworkStatus.ONLINE:
            self._check_for_updates()
        return {"status": "check_initiated"}

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an item from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            The cached data or None if not found
        """
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute('SELECT data, timestamp FROM cache WHERE key = ?', (key,))
                result = cursor.fetchone()
                
                if result:
                    data, timestamp = result
                    return {
                                'data': json.loads(data),
                                'status': self._get_status(timestamp),
                                'timestamp': timestamp
                            }
                return None
            except sqlite3.Error as e:
                logger.error(f"Error retrieving from cache: {e}")
                return None
                
    def set(self, key: str, data: Any, sync: bool = True) -> bool:
        """
        Store an item in the cache.
        
        Args:
            key: The cache key
            data: The data to cache
            sync: Whether to sync this change to the server
            
        Returns:
            True if successful, False otherwise
        """
        timestamp = int(time.time())
        json_data = json.dumps(data)
        sync_status = 'pending' if sync else 'synced'
        
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute(
                    'INSERT OR REPLACE INTO cache (key, data, timestamp, sync_status) VALUES (?, ?, ?, ?)',
                    (key, json_data, timestamp, sync_status)
                )
                self.conn.commit()
                
                # If sync is required, add to sync queue
                if sync and services.sync_service is not None:
                    # Here we're using the services registry instead of direct import
                    service = services.sync_service
                    service.queue_update(model_type=key.split(':')[0], 
                                        model_id=key.split(':')[1], 
                                        data=data,
                                        priority=QueuePriority.NORMAL)
                
                return True
            except sqlite3.Error as e:
                logger.error(f"Error storing in cache: {e}")
                return False
                
    def _get_status(self, timestamp: int) -> CacheStatus:
        """
        Determine the status of a cached item based on its timestamp.
        
        Args:
            timestamp: The cache entry timestamp
            
        Returns:
            The appropriate CacheStatus
        """
        now = int(time.time())
        age = now - timestamp
        
        if age < self.ttl_fresh:
            return CacheStatus.FRESH
        elif age < self.ttl_stale:
            return CacheStatus.STALE
        else:
            return CacheStatus.EXPIRED
            
    # Additional methods for cache management
    
    def invalidate(self, key: str) -> bool:
        """
        Invalidate a specific cache entry.
        
        Args:
            key: The cache key to invalidate
            
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute('DELETE FROM cache WHERE key = ?', (key,))
                self.conn.commit()
                return cursor.rowcount > 0
            except sqlite3.Error as e:
                logger.error(f"Error invalidating cache: {e}")
                return False
                
    def invalidate_collection(self, collection: str) -> int:
        """
        Invalidate all cache entries for a collection.
        
        Args:
            collection: The collection name (prefix of the cache keys)
            
        Returns:
            Number of invalidated entries
        """
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute('DELETE FROM cache WHERE key LIKE ?', (f"{collection}:%",))
                self.conn.commit()
                return cursor.rowcount
            except sqlite3.Error as e:
                logger.error(f"Error invalidating collection: {e}")
                return 0
                
    def cleanup(self) -> int:
        """
        Remove expired entries from the cache.
        
        Returns:
            Number of removed entries
        """
        expiry_time = int(time.time()) - self.ttl_stale
        
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute('DELETE FROM cache WHERE timestamp < ?', (expiry_time,))
                self.conn.commit()
                return cursor.rowcount
            except sqlite3.Error as e:
                logger.error(f"Error during cache cleanup: {e}")
                return 0
                
    def get_collection(self, collection: str) -> List[Dict[str, Any]]:
        """
        Retrieve all items for a collection.
        
        Args:
            collection: The collection name (prefix of the cache keys)
            
        Returns:
            List of cache entries
        """
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute('SELECT key, data, timestamp FROM cache WHERE key LIKE ?', (f"{collection}:%",))
                results = cursor.fetchall()
                
                return [{
                    'key': key,
                    'data': json.loads(data),
                    'status': self._get_status(timestamp),
                    'timestamp': timestamp
                } for key, data, timestamp in results]
            except sqlite3.Error as e:
                logger.error(f"Error retrieving collection: {e}")
                return []
                
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Cache database connection closed")

    def get_subject_cache_status(self, subject: str, level: str) -> dict:
        """
        Get cache status information for a specific subject and level.
        
        Returns:
            dict: A dictionary containing:
                - status: CacheStatus value (FRESH, STALE, EXPIRED, INVALID)
                - last_updated: timestamp of last update
                - completion_percentage: percentage of cached content (0-100)
                - progress_status: CacheProgressStatus value (IDLE, SYNCING, DOWNLOADING, ERROR)
        """
        try:
            # Initialize default response (includes question_count: 0 initially)
            result = {
                'status': CacheStatus.INVALID,
                'last_updated': None,
                'question_count': 0, # Initial default
                'completion_percentage': 0,
                'progress_status': CacheProgressStatus.IDLE
            }
            
            # IMPORTANT: The UI expects subject/level/year structure
            subject_dir = os.path.join(self.QUESTIONS_DIR, self._safe_filename(subject))
            level_dir = os.path.join(subject_dir, level)  # The UI expects level to be a direct subdirectory
            
            logger.debug(f"Checking cache at path: {level_dir}")
            
            # If the level directory doesn't exist, there's no cached content
            if not os.path.exists(level_dir):
                logger.debug(f"Level directory not found: {level_dir}")
                return result
                
            # Check if level directory has any content (years with question files)
            has_content = False
            question_count = 0 # Variable to store the count
            years_found = []
            last_updated = None
            
            # Count questions in each year directory
            for item in os.listdir(level_dir):
                year_dir = os.path.join(level_dir, item)
                if os.path.isdir(year_dir):
                    question_files = [f for f in os.listdir(year_dir) if f.endswith('.json')]
                    if question_files:
                        has_content = True
                        years_found.append(item)
                        question_count += len(question_files) # Count is calculated here

            if not has_content:
                logger.debug(f"No question files found in level directory: {level_dir}")
                return result
            
            # If we found content, log it
            logger.info(f"Found {question_count} cached questions for {subject}/{level} across {len(years_found)} years")
            
            # Try to get the last updated timestamp from metadata
            metadata_path = os.path.join(self.METADATA_DIR, 'subjects.json')
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    
                    # Get the timestamp from metadata if available
                    if subject in metadata and level in metadata[subject]:
                        last_updated = metadata[subject][level].get('last_updated')
                        logger.debug(f"Found metadata timestamp: {last_updated}")
                    else:
                        # Use directory modification time as fallback
                        last_updated = os.path.getmtime(level_dir)
                        logger.debug(f"Using directory modification time: {last_updated}")
                except Exception as e:
                    logger.error(f"Error reading metadata: {e}")
                    # Use directory modification time as fallback
                    last_updated = os.path.getmtime(level_dir)
            else:
                # Use directory modification time if no metadata
                last_updated = os.path.getmtime(level_dir)
                logger.debug(f"Using directory modification time (no metadata): {last_updated}")
            
            # Update result with found data
            result['last_updated'] = last_updated
            
            # Set completion percentage based on question count
            if question_count > 0:
                result['completion_percentage'] = min(100, 50 + question_count * 2.5)
                
                # Set status based on timestamp
                if last_updated:
                    age = time.time() - last_updated
                    if age < self.ttl_fresh:
                        result['status'] = CacheStatus.FRESH
                    else:
                        result['status'] = CacheStatus.STALE
            
            # Add the calculated count to the result
            result['question_count'] = question_count
            
            logger.debug(f"Final cache status for {subject}/{level}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting subject cache status: {e}", exc_info=True)
            # Return default structure on error, which already includes question_count: 0
            return {
                'status': CacheStatus.INVALID,
                'last_updated': None,
                'question_count': 0,
                'completion_percentage': 0,
                'progress_status': CacheProgressStatus.ERROR # Update status on error
            }
            
    def _count_cached_questions(self, subject: str, level: str) -> int:
        """Count actual cached questions for a subject/level by examining file system"""
        try:
            total_questions = 0
            subject_path = os.path.join(self.QUESTIONS_DIR, self._safe_filename(subject))
            
            if not os.path.exists(subject_path):
                return 0
                
            # Check if level directory exists
            level_path = os.path.join(subject_path, level)
            if os.path.exists(level_path) and os.path.isdir(level_path):
                # Count questions in each year directory
                for year in os.listdir(level_path):
                    year_path = os.path.join(level_path, year)
                    if os.path.isdir(year_path):
                        question_files = [f for f in os.listdir(year_path) if f.endswith('.json')]
                        total_questions += len(question_files)
            else:
                # Try alternate structure: check if years are direct children of subject dir
                for year in os.listdir(subject_path):
                    year_path = os.path.join(subject_path, year)
                    if os.path.isdir(year_path):
                        question_files = [f for f in os.listdir(year_path) if f.endswith('.json')]
                        total_questions += len(question_files)
            
            return total_questions
            
        except Exception as e:
            logger.error(f"Error counting cached questions: {e}")
            return 0
    
    def _get_subject_last_updated(self, subject: str, level: str) -> Optional[float]:
        """Get the timestamp when the subject/level was last updated"""
        try:
            # Check if we have metadata for this subject/level
            subject_dir = os.path.join(self.METADATA_DIR, self._safe_filename(subject), self._safe_filename(level))
            if not os.path.exists(subject_dir):
                return None
            
            # Get the metadata file
            metadata_file = os.path.join(subject_dir, "metadata.json")
            if not os.path.exists(metadata_file):
                return None
            
            # Load the metadata
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            return metadata.get('last_updated')
        
        except Exception as e:
            logger.error(f"Error getting subject last updated: {e}")
            return None
    
    def _get_subject_progress_status(self, subject: str, level: str) -> str:
        """Get the current progress status for a subject/level"""
        try:
            # Check if this subject/level is currently syncing or downloading
            # This would typically be stored in a tracking variable or database
            
            # For now, we'll just return IDLE
            # In a real implementation, you would track active operations
            # and return the appropriate status
            return CacheProgressStatus.IDLE
            
        except Exception as e:
            logger.error(f"Error getting subject progress status: {e}")
            return CacheProgressStatus.IDLE
    
    def get_all_subjects_cache_status(self) -> Dict[str, Dict[str, dict]]:
        """
        Get cache status information for all subjects and levels.
        
        Returns:
            Dict[str, Dict[str, dict]]: A nested dictionary containing:
                {
                    'subject1': {
                        'level1': {status_info},
                        'level2': {status_info}
                    },
                    'subject2': {...}
                }
                
                Where status_info is the same as returned by get_subject_cache_status()
        """
        try:
            # Initialize empty result
            result = {}
            
            # Check if metadata directory exists
            if not os.path.exists(self.METADATA_DIR):
                return result
            
            # Iterate through subject directories
            for subject_dir in os.listdir(self.METADATA_DIR):
                subject_path = os.path.join(self.METADATA_DIR, subject_dir)
                if not os.path.isdir(subject_path):
                    continue
                
                subject = subject_dir  # This assumes directory name matches subject name
                result[subject] = {}
                
                # Iterate through level directories
                for level_dir in os.listdir(subject_path):
                    level_path = os.path.join(subject_path, level_dir)
                    if not os.path.isdir(level_path):
                        continue
                    
                    level = level_dir  # This assumes directory name matches level name
                    
                    # Get status for this subject/level
                    status = self.get_subject_cache_status(subject, level)
                    result[subject][level] = status
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting all subjects cache status: {e}")
            return {}

    def get_random_question(self, subject_name: str, level_key: str) -> dict | None:
        """
        Get a random cached question and its corresponding answer from local storage.

        Args:
            subject_name: Subject name
            level_key: Level key

        Returns:
            Dictionary containing question data and correct answer data, or None if not found.
        """
        self.logger.debug(f"Attempting to get random question for {subject_name}/{level_key}")
        is_active = self.is_subscribed()

        try:
            # --- Find all available question files ---
            # --- START: Restore file finding logic ---
            safe_subject = self._safe_filename(subject_name)
            level_path = os.path.join(self.QUESTIONS_DIR, safe_subject, level_key)
            self.logger.debug(f"Constructed level path for questions: {level_path}")

            all_question_files = [] # Initialize the list HERE

            if not os.path.isdir(level_path):
                self.logger.warning(f"Questions directory not found for {subject_name}/{level_key} at {level_path}")
                # No need to return yet, check if all_question_files is empty later
            else:
                 # Walk through year subdirectories
                 self.logger.debug(f"Searching for year subdirectories in: {level_path}")
                 for year_dir_name in os.listdir(level_path):
                     year_path = os.path.join(level_path, year_dir_name)
                     self.logger.debug(f"Checking path: {year_path}")
                     if os.path.isdir(year_path):
                         self.logger.debug(f"Found year directory: {year_path}. Searching for JSON files...")
                         for filename in os.listdir(year_path):
                             if filename.endswith('.json'):
                                 full_path = os.path.join(year_path, filename)
                                 self.logger.debug(f"Found question file: {full_path}")
                                 all_question_files.append(full_path)
                     else:
                          self.logger.debug(f"Skipping item (not a directory): {year_path}")
            # --- END: Restore file finding logic ---

            # --- Now the check makes sense ---
            if not all_question_files:
                self.logger.warning(f"No cached question JSON files found in {level_path} or its subdirectories.")
                return None # Return None if no files were found

            self.logger.debug(f"Found {len(all_question_files)} potential question files for {subject_name}/{level_key}.")

            # --- Select a random question file ---
            selected_question_file = random.choice(all_question_files)
            self.logger.info(f"Selected random question file: {selected_question_file}")

            # --- Load question data ---
            question_data = None
            try:
                with open(selected_question_file, 'r', encoding='utf-8') as f:
                    question_data = json.load(f)
                self.logger.debug(f"Successfully loaded question data from {selected_question_file}:\n{pprint.pformat(question_data)}") # Added pretty print
            except json.JSONDecodeError as e:
                self.logger.error(f"Error decoding JSON from question file {selected_question_file}: {e}")
                return None
            except IOError as e:
                 self.logger.error(f"Error reading question file {selected_question_file}: {e}")
                 return None

            if not question_data:
                 self.logger.error(f"Failed to load question data from {selected_question_file} despite no exception.")
                 return None

            # --- Resolve asset paths ---
            self._resolve_asset_paths(question_data)

            # --- Load corresponding answer data ---
            correct_answer_data = None
            answer_ref = question_data.get('answer_ref')
            self.logger.debug(f"Extracted answer_ref from question data: '{answer_ref}' (Type: {type(answer_ref)})")

            if answer_ref and isinstance(answer_ref, str):
                self.logger.debug(f"Found valid answer_ref: {answer_ref}. Proceeding to find answer file.")
                try:
                    # Construct answer file path
                    question_dir = os.path.dirname(selected_question_file)
                    self.logger.debug(f"Calculated question_dir: {question_dir}") # Log question dir
                    # Navigate up: year -> level -> subject -> questions_base
                    # CORRECTED LOGIC: Need to go up TWICE from question_dir (which is inside 'year')
                    # to get to the 'level' directory containing year folders.
                    base_level_dir = os.path.dirname(question_dir) # e.g., src/data/cache/questions/biology/o_level
                    self.logger.debug(f"Calculated base_level_dir (containing year folders): {base_level_dir}") # Log base level dir

                    # Construct path into the parallel 'answers' directory
                    answers_base_dir_candidate = base_level_dir.replace(self.QUESTIONS_DIR, os.path.join(self.ANSWERS_DIR, "answers"), 1)
                    self.logger.debug(f"Candidate answers_base_dir (after replace): {answers_base_dir_candidate}") # Log candidate answer base

                    # Check if replacement worked, otherwise construct manually (safer)
                    if self.QUESTIONS_DIR not in base_level_dir:
                         self.logger.warning("QUESTIONS_DIR not found in base_level_dir, path replacement might be incorrect. Constructing manually.")
                         # Example manual construction (adjust if base structure differs)
                         parts = base_level_dir.split(os.sep)
                         if len(parts) >= 5 and parts[-4] == 'data' and parts[-3] == 'cache' and parts[-2] == 'questions':
                              answers_base_dir_candidate = os.path.join(os.sep.join(parts[:-2]), 'answers', parts[-1]) # Combine parts, swap 'questions' for 'answers'
                              self.logger.debug(f"Manually constructed answers_base_dir: {answers_base_dir_candidate}") # Log manually constructed path
                         else:
                              self.logger.error("Cannot reliably construct parallel answers directory path.")
                              answers_base_dir_candidate = None # Signal error

                    if answers_base_dir_candidate:
                         answer_file_path = os.path.join(
                            answers_base_dir_candidate, # Path like src/data/cache/answers/biology/o_level
                            os.path.basename(question_dir), # year subdir name (e.g., 2024)
                            answer_ref # The answer filename (e.g., "1.json")
                         )
                         self.logger.info(f"Constructed potential answer file path: {answer_file_path}")

                         answer_file_exists = os.path.exists(answer_file_path)
                         self.logger.info(f"Checking existence of answer file at '{answer_file_path}': {answer_file_exists}")

                         if answer_file_exists:
                            self.logger.debug(f"Attempting to open and load JSON from: {answer_file_path}")
                            with open(answer_file_path, 'r', encoding='utf-8') as f_ans:
                                self.logger.debug(f"Opened answer file. Attempting json.load...")
                                correct_answer_data = json.load(f_ans)
                                # <<< --- LOGGING ADDED: Raw Answer Object from File --- >>>
                                self.logger.debug(f"Successfully loaded RAW answer object from file ({answer_file_path}):\n{pprint.pformat(correct_answer_data)}")
                                # <<< --- END LOGGING ADDED --- >>>
                                self.logger.debug(f"Successfully loaded JSON from answer file. Type: {type(correct_answer_data)}")
                            self.logger.info(f"Successfully loaded answer data for {answer_ref}")
                         else:
                            self.logger.warning(f"Answer file referenced by {answer_ref} was NOT FOUND at the calculated path: {answer_file_path}")
                    else:
                         self.logger.error("Could not construct path to answers directory.")

                except json.JSONDecodeError as e:
                    # Use answer_file_path if defined, otherwise indicate it wasn't
                    log_path = answer_file_path if 'answer_file_path' in locals() else "UNKNOWN PATH"
                    self.logger.error(f"JSONDecodeError while reading answer file {log_path}: {e}") # Log JSON errors
                    correct_answer_data = None
                except IOError as e:
                    # Use answer_file_path if defined, otherwise indicate it wasn't
                    log_path = answer_file_path if 'answer_file_path' in locals() else "UNKNOWN PATH"
                    self.logger.error(f"IOError reading answer file {log_path}: {e}") # Log IO errors
                    correct_answer_data = None
                except NameError: # Catch if answer_file_path wasn't defined
                    self.logger.error("Could not attempt to read answer file because its path was not determined.") # Log NameError
                    correct_answer_data = None
                except Exception as e:
                    self.logger.error(f"Unexpected error loading answer file for {answer_ref}: {e}", exc_info=True) # Log other exceptions
                    correct_answer_data = None
            else:
                self.logger.warning(f"No valid 'answer_ref' string found in question data from {selected_question_file}. Cannot load answer.")

            self.logger.debug(f"Value of correct_answer_data before assigning to question_data: {correct_answer_data is not None} (Type: {type(correct_answer_data)})")
            question_data['correct_answer_data'] = correct_answer_data

            if not is_active:
                question_data['subscription_expired'] = True
                self.logger.warning(f"Subscription is not active, adding warning flag to returned data for {selected_question_file}")

            # --- CHANGE TO INFO ---
            self.logger.info(f"Final combined question_data dictionary being returned for {selected_question_file}:\n{pprint.pformat(question_data)}")
            # --- END CHANGE ---
            return question_data

        except Exception as e:
            self.logger.error(f"Error during get_random_question for {subject_name}/{level_key}: {e}", exc_info=True)
            return None

    def _handle_network_change(self, status: NetworkStatus):
        """Handle network status changes detected by the NetworkMonitor."""
        # Use the logger initialized in __init__
        if not hasattr(self, 'logger'): # Safety check for logger
             print("ERROR: Logger not initialized in CacheManager when _handle_network_change called.")
             return

        self.logger.debug(f"Network status change signal received: {status}")
        # Trigger check only if status is ONLINE and the manager is supposed to be running
        if status == NetworkStatus.ONLINE and hasattr(self, 'running') and self.running:
            self.logger.info("Network status changed to ONLINE. Triggering cache update check.")
            # Run the check in a separate thread to avoid blocking the signal handler
            # Ensure _perform_online_update_check exists
            if hasattr(self, '_perform_online_update_check'):
                 online_check_thread = threading.Thread(
                     target=self._perform_online_update_check,
                     args=("Network Online Event",), # Pass reason for logging
                     daemon=True
                 )
                 online_check_thread.start()
            else:
                 self.logger.error("Cannot trigger online update check: _perform_online_update_check method is missing.")
        elif status != NetworkStatus.ONLINE:
            self.logger.info(f"Network status changed to {status}. Cache updates paused if running.")

    def _perform_online_update_check(self, trigger_reason: str):
        self.logger.info(f"Performing online update check, triggered by: {trigger_reason}")
        # This method should now primarily focus on triggering the check
        # The actual work (downloading and syncing) happens in _check_for_updates
        self._check_for_updates()
        
        # REMOVED from here: self.sync_all_local_cache_to_db() 

    # --- MODIFIED SYNC FUNCTION (v3 with v4 Debugging) ---
    def sync_question_cache_to_db(self):
        """
        Scans the JSON question cache files to populate the cached_questions SQLAlchemy table.
        Each paper JSON contains multiple sub-questions which are stored as individual rows.
        """
        self.logger.info(">>> SYNC_DB: Starting sync (Paper ID + SubQs)...")
        inserted_count = 0
        updated_count = 0
        checked_files_count = 0
        processed_subquestions_count = 0
        skipped_malformed_paper = 0
        skipped_missing_paper_id = 0
        skipped_missing_subq_fields = 0

        try:
            with get_db_session() as session:
                # Ensuring table exists (won't alter columns)
                try:
                    CachedQuestion.__table__.create(session.bind, checkfirst=True)
                    session.commit()
                    self.logger.info(">>> SYNC_DB: Ensured 'cached_questions' table exists.")
                except Exception as table_err:
                    self.logger.error(f">>> SYNC_DB: Error ensuring table exists: {table_err}", exc_info=True)
                    session.rollback()
                    return

                if not os.path.exists(self.QUESTIONS_DIR):
                    self.logger.warning(f">>> SYNC_DB: Question cache directory NOT FOUND: {self.QUESTIONS_DIR}.")
                    return
                self.logger.info(f">>> SYNC_DB: Scanning cache directory: {self.QUESTIONS_DIR}")

                for subject_dir in os.listdir(self.QUESTIONS_DIR):
                    subject_path = os.path.join(self.QUESTIONS_DIR, subject_dir)
                    if not os.path.isdir(subject_path): continue
                    subject_name_from_dir = subject_dir

                    for level_dir in os.listdir(subject_path):
                        level_path = os.path.join(subject_path, level_dir)
                        if not os.path.isdir(level_path): continue
                        level_name_from_dir = level_dir

                        for year_dir in os.listdir(level_path):
                            year_path = os.path.join(level_path, year_dir)
                            if not os.path.isdir(year_path): continue
                            year_from_dir_str = year_dir
                            try:
                                paper_year_from_dir = int(year_from_dir_str)
                            except ValueError:
                                self.logger.warning(f">>> SYNC_DB: Invalid year directory name '{year_from_dir_str}' in {level_path}. Skipping.")
                                continue

                            for filename in os.listdir(year_path):
                                if filename.endswith(".json"):
                                    file_path = os.path.join(year_path, filename)
                                    self.logger.debug(f">>> SYNC_DB: Processing Paper File: {file_path}")
                                    checked_files_count += 1
                                    question_paper_json_data = None
                                    try:
                                        with open(file_path, 'r', encoding='utf-8') as f:
                                            question_paper_json_data = json.load(f)
                                    except json.JSONDecodeError:
                                        self.logger.warning(f">>> SYNC_DB: Malformed JSON for paper: {file_path}")
                                        skipped_malformed_paper += 1
                                        continue
                                    except IOError as e:
                                        self.logger.error(f">>> SYNC_DB: IOError reading paper file {file_path}: {e}")
                                        continue

                                    # --- Extract Paper-Level Data ---
                                    paper_document_id_from_json = str(question_paper_json_data.get('id') or question_paper_json_data.get('_id'))
                                    if not paper_document_id_from_json or paper_document_id_from_json == 'None':
                                        self.logger.warning(f">>> SYNC_DB: Missing 'id' or '_id' for paper in {file_path}.")
                                        skipped_missing_paper_id += 1
                                        continue

                                    paper_topic_from_json = question_paper_json_data.get('topic')
                                    paper_subtopic_from_json = question_paper_json_data.get('subtopic')
                                    paper_difficulty_json_obj = question_paper_json_data.get('difficulty')
                                    paper_difficulty_level_str = None
                                    if isinstance(paper_difficulty_json_obj, dict):
                                        paper_difficulty_level_str = paper_difficulty_json_obj.get('level')
                                    elif isinstance(paper_difficulty_json_obj, str):
                                        paper_difficulty_level_str = paper_difficulty_json_obj
                                    subject_from_json = question_paper_json_data.get('subject', subject_name_from_dir)
                                    level_from_json = question_paper_json_data.get('level', level_name_from_dir)

                                    # --- Iterate through sub_questions ---
                                    sub_questions_array = question_paper_json_data.get('sub_questions', [])
                                    if not isinstance(sub_questions_array, list):
                                         self.logger.warning(f">>> SYNC_DB: 'sub_questions' is not a list in {file_path}. Skipping sub-questions.")
                                         sub_questions_array = []

                                    for sub_q_item_json in sub_questions_array:
                                        processed_subquestions_count +=1
                                        q_number_str_from_sub_q = sub_q_item_json.get('sub_number')
                                        q_content_from_sub_q = sub_q_item_json.get('text')
                                        q_marks_raw_from_sub_q = sub_q_item_json.get('marks')

                                        if not all([q_number_str_from_sub_q, q_content_from_sub_q, q_marks_raw_from_sub_q is not None]):
                                            self.logger.warning(f">>> SYNC_DB: Sub-question in {paper_document_id_from_json} (file: {filename}) missing sub_number, text, or marks. Data: {sub_q_item_json}")
                                            skipped_missing_subq_fields +=1
                                            continue
                                        try:
                                            q_marks_from_sub_q = int(q_marks_raw_from_sub_q)
                                        except (ValueError, TypeError):
                                            self.logger.warning(f">>> SYNC_DB: Invalid marks '{q_marks_raw_from_sub_q}' for sub_question {q_number_str_from_sub_q} in {paper_document_id_from_json} (file: {filename}).")
                                            skipped_missing_subq_fields +=1
                                            continue

                                        current_unique_question_key = f"{paper_document_id_from_json}_{q_number_str_from_sub_q}"
                                        existing_question_record = session.query(CachedQuestion).filter_by(unique_question_key=current_unique_question_key).first()

                                        if existing_question_record:
                                            updated_this_run = False
                                            if existing_question_record.content != q_content_from_sub_q:
                                                existing_question_record.content = q_content_from_sub_q; updated_this_run = True
                                            if existing_question_record.marks != q_marks_from_sub_q:
                                                existing_question_record.marks = q_marks_from_sub_q; updated_this_run = True
                                            if (existing_question_record.topic != paper_topic_from_json and paper_topic_from_json is not None) or \
                                               (existing_question_record.topic is None and paper_topic_from_json is not None) :
                                                existing_question_record.topic = paper_topic_from_json; updated_this_run = True
                                            if (existing_question_record.subtopic != paper_subtopic_from_json and paper_subtopic_from_json is not None) or \
                                               (existing_question_record.subtopic is None and paper_subtopic_from_json is not None):
                                                existing_question_record.subtopic = paper_subtopic_from_json; updated_this_run = True
                                            if (existing_question_record.difficulty != paper_difficulty_level_str and paper_difficulty_level_str is not None) or \
                                               (existing_question_record.difficulty is None and paper_difficulty_level_str is not None):
                                                existing_question_record.difficulty = paper_difficulty_level_str; updated_this_run = True
                                            if existing_question_record.subject != subject_from_json: existing_question_record.subject = subject_from_json; updated_this_run = True
                                            if existing_question_record.level != level_from_json: existing_question_record.level = level_from_json; updated_this_run = True
                                            if existing_question_record.paper_year != paper_year_from_dir: existing_question_record.paper_year = paper_year_from_dir; updated_this_run = True

                                            if updated_this_run:
                                                existing_question_record.last_accessed = datetime.now()
                                                updated_count += 1
                                                self.logger.info(f">>> SYNC_DB_UPDATE: Updated question key {current_unique_question_key}.")
                                        else:
                                            now = datetime.now()
                                            new_question_record = CachedQuestion(
                                                unique_question_key=current_unique_question_key,
                                                paper_document_id=paper_document_id_from_json,
                                                question_number_str=q_number_str_from_sub_q,
                                                paper_year=paper_year_from_dir,
                                                subject=subject_from_json,
                                                level=level_from_json,
                                                topic=paper_topic_from_json,
                                                subtopic=paper_subtopic_from_json,
                                                difficulty=paper_difficulty_level_str,
                                                content=q_content_from_sub_q,
                                                marks=q_marks_from_sub_q,
                                                cached_at=now,
                                                last_accessed=now
                                            )
                                            session.add(new_question_record)
                                            inserted_count += 1
                                            self.logger.info(f">>> SYNC_DB_INSERT: Added question key {current_unique_question_key}.")

            # Final commit after all processing
            session.commit()
            self.logger.info(f">>> SYNC_DB: Finished sync. Checked Files: {checked_files_count}, Processed SubQs: {processed_subquestions_count}, Inserted: {inserted_count}, Updated: {updated_count}, Skipped (Malformed Paper): {skipped_malformed_paper}, Skipped (No Paper ID): {skipped_missing_paper_id}, Skipped (SubQ w/ Missing Fields): {skipped_missing_subq_fields}")

        except Exception as e:
            self.logger.error(f">>> SYNC_DB: Critical error during sync: {e}", exc_info=True)

    def sync_answers_to_db(self):
        """
        Scans the local answers cache directory (data/cache/answers) and syncs 
        individual sub-answers to the 'cached_answers' table in the main database.
        Relies on corresponding question JSON files to link via paper_document_id.
        """
        self.logger.info(">>> SYNC_ANSWERS_DB: Starting answer sync to database...")
        checked_answer_files = 0
        processed_sub_answers = 0
        inserted_answers = 0
        updated_answers = 0
        skipped_answers_no_question_file = 0
        skipped_answers_no_paper_id = 0
        skipped_answers_other_error = 0

        if not os.path.exists(self.ANSWERS_DIR):
            self.logger.warning(f">>> SYNC_ANSWERS_DB: Answers directory does not exist: {self.ANSWERS_DIR}")
            return

        with get_db_session() as session:
            try:
                for subject_name in os.listdir(self.ANSWERS_DIR):
                    subject_path = os.path.join(self.ANSWERS_DIR, subject_name)
                    if not os.path.isdir(subject_path): continue

                    for level_name in os.listdir(subject_path):
                        level_path = os.path.join(subject_path, level_name)
                        if not os.path.isdir(level_path): continue

                        for year_name in os.listdir(level_path):
                            year_path = os.path.join(level_path, year_name)
                            if not os.path.isdir(year_path): continue

                            for answer_filename in os.listdir(year_path):
                                if not answer_filename.endswith(".json"): continue
                                
                                checked_answer_files += 1
                                answer_filepath = os.path.join(year_path, answer_filename)
                                # Main question number from answer filename (e.g., "1" from "1.json")
                                main_question_number_str_from_ans_file = answer_filename[:-5] 

                                # Construct path to the corresponding main question file
                                # Use the main question number here for the lookup
                                corresponding_question_filepath = os.path.join(
                                    self.QUESTIONS_DIR, subject_name, level_name, year_name,
                                    f"{main_question_number_str_from_ans_file}.json" 
                                )

                                if not os.path.exists(corresponding_question_filepath):
                                    self.logger.warning(f">>> SYNC_ANSWERS_DB: Corresponding question file not found for answer {answer_filepath} at {corresponding_question_filepath}. Skipping.")
                                    skipped_answers_no_question_file += 1
                                    continue
                                
                                try:
                                    # Get paper_document_id from the question file
                                    with open(corresponding_question_filepath, 'r', encoding='utf-8') as qf:
                                        question_data_from_file = json.load(qf)
                                    paper_document_id = question_data_from_file.get("id")
                                    if not paper_document_id:
                                        self.logger.warning(f">>> SYNC_ANSWERS_DB: 'id' (paper_document_id) not found in question file {corresponding_question_filepath}. Skipping answer file {answer_filepath}.")
                                        skipped_answers_no_paper_id += 1
                                        continue

                                    # Read the answer file which contains sub-answers
                                    with open(answer_filepath, 'r', encoding='utf-8') as af:
                                        full_answer_data_from_file = json.load(af)
                                    
                                    # Iterate through sub-answers within the answer file
                                    sub_answer_list = []
                                    if isinstance(full_answer_data_from_file.get("answers"), list) and len(full_answer_data_from_file["answers"]) > 0:
                                         # Assuming the structure shown in the example 1.json
                                         sub_answer_list = full_answer_data_from_file["answers"][0].get("sub_answers", [])
                                    
                                    if not sub_answer_list:
                                        self.logger.warning(f">>> SYNC_ANSWERS_DB: No 'sub_answers' array found or empty in {answer_filepath}. Skipping.")
                                        skipped_answers_other_error += 1
                                        continue

                                    for sub_answer_obj in sub_answer_list:
                                        if not isinstance(sub_answer_obj, dict): continue

                                        sub_number = sub_answer_obj.get("sub_number") # e.g., "a(i)"
                                        if not sub_number:
                                            self.logger.warning(f">>> SYNC_ANSWERS_DB: Missing 'sub_number' in sub-answer within {answer_filepath}. Sub-answer data: {sub_answer_obj}")
                                            skipped_answers_other_error += 1
                                            continue

                                        processed_sub_answers += 1
                                        # Construct the specific unique key for this sub-answer
                                        unique_question_key = f"{paper_document_id}_{sub_number}"
                                        
                                        # Find existing or create new CachedAnswer entry
                                        existing_answer = session.query(CachedAnswer).filter_by(cached_question_unique_key=unique_question_key).first()

                                        # The content to store is the sub_answer object itself
                                        answer_content_to_store = sub_answer_obj 

                                        if existing_answer:
                                            if existing_answer.answer_content != answer_content_to_store:
                                                existing_answer.answer_content = answer_content_to_store
                                                existing_answer.updated_at = datetime.now()
                                                # existing_answer.answer_source_tag = "filesystem_sync_vY" 
                                                updated_answers += 1
                                                self.logger.debug(f">>> SYNC_ANSWERS_DB_UPDATE: Updated answer for Q_Key {unique_question_key}")
                                        else:
                                            new_answer = CachedAnswer(
                                                cached_question_unique_key=unique_question_key,
                                                answer_content=answer_content_to_store,
                                                # answer_source_tag="filesystem_sync_vY", 
                                                created_at=datetime.now(),
                                                updated_at=datetime.now()
                                            )
                                            session.add(new_answer)
                                            inserted_answers += 1
                                            self.logger.debug(f">>> SYNC_ANSWERS_DB_INSERT: Added answer for Q_Key {unique_question_key}")

                                except json.JSONDecodeError as e:
                                    self.logger.error(f">>> SYNC_ANSWERS_DB: Error decoding JSON from {answer_filepath} or {corresponding_question_filepath}: {e}")
                                    skipped_answers_other_error += 1
                                except Exception as e:
                                    self.logger.error(f">>> SYNC_ANSWERS_DB: Error processing answer file {answer_filepath} or its question file: {e}", exc_info=True)
                                    skipped_answers_other_error += 1
                
                session.commit() # Commit changes after processing all files
                self.logger.info(f">>> SYNC_ANSWERS_DB: Finished answer sync. Checked Files: {checked_answer_files}, Processed Sub-Answers: {processed_sub_answers}, Inserted: {inserted_answers}, Updated: {updated_answers}, Skipped (No Q-File): {skipped_answers_no_question_file}, Skipped (No PaperID): {skipped_answers_no_paper_id}, Skipped (Other): {skipped_answers_other_error}")

            except Exception as e:
                session.rollback()
                self.logger.error(f">>> SYNC_ANSWERS_DB: Major error during answer sync transaction: {e}", exc_info=True)
            finally:
                self.logger.info(">>> SYNC_ANSWERS_DB: Answer sync process attempt finished.")

    def sync_all_local_cache_to_db(self):
        """Coordinates syncing all relevant local cache data to the main database."""
        self.logger.info(">>> SYNC_ALL_TO_DB: Starting full local cache to DB sync...")
        try:
            self.sync_question_cache_to_db() # Sync questions first
            self.sync_answers_to_db()      # Then sync answers
        except Exception as e:
             self.logger.error(f">>> SYNC_ALL_TO_DB: Error during sync process: {e}", exc_info=True)
        finally:
             self.logger.info(">>> SYNC_ALL_TO_DB: Full local cache to DB sync finished.")
