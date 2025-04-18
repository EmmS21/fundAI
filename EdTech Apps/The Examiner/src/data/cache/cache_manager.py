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
    CACHE_DIR = os.path.join("src", "data", "cache")
    METADATA_DIR = os.path.join(CACHE_DIR, "metadata")
    ASSETS_DIR = os.path.join(CACHE_DIR, "assets")
    QUESTIONS_DIR = os.path.join(CACHE_DIR, "questions")
    
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
        """Check if there are updates available for the cached content"""
        logger.info("Checking for cache updates...")
        
        try:
            # Check current MongoDB connection
            mongo_client = MongoDBClient()
            connected = mongo_client.connected and mongo_client.initialized
            logger.info(f"MongoDB connection result: {connected}")
            
            if not connected:
                logger.warning("MongoDB not connected, skipping cache update check")
                return
                
            logger.info("MongoDB connected, checking for new content...")
            
            # No need to import again, already imported at top of file
            user = UserOperations.get_current_user()
            
            # If no user found, we can't determine what to cache
            if not user:
                logger.warning("No user found, skipping cache update check")
                return
                
            # Get subjects enabled by the user
            subjects = UserOperations.get_user_subjects()
            
            if not subjects:
                logger.warning("No subjects found for user, skipping cache update check")
                return
                
            # Process each subject
            for subject in subjects:
                # Get the subject name directly from the dictionary
                subject_name = subject['name']
                
                logger.debug(f"Checking updates for subject: {subject_name} (ID: {subject['subject_id']})")
                
                # Access levels from the dictionary
                levels = subject['levels']
                enabled_levels = {
                    'grade_7': levels.get('grade_7', False),
                    'o_level': levels.get('o_level', False),
                    'a_level': levels.get('a_level', False)
                }
                
                # Get only enabled levels
                for level_key, enabled in enabled_levels.items():
                    if not enabled:
                        continue
                        
                    # Convert level key to MongoDB format
                    mongo_level = self._convert_level_to_mongo_format(level_key)
                    
                    # Get last update time for this subject/level
                    last_update = self._get_subject_last_updated(subject_name, level_key)
                    
                    # Skip if updated recently (only check max once per hour)
                    if last_update and (time.time() - last_update < 3600):  # 1 hour
                        logger.debug(f"Subject {subject_name}/{level_key} recently updated, skipping")
                        continue
                        
                    # Queue this subject for update
                    logger.info(f"Queuing update check for {subject_name}/{level_key}")
                    self._queue_questions_for_caching(subject_name, level_key, mongo_level)
            
        except Exception as e:
            logger.error(f"Error checking for updates: {e}", exc_info=True)
    
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
            
    def _queue_questions_for_caching(self, subject: str, level_key: str, mongo_level: str):
        """Queue questions for the specified subject and level for caching."""
        self.logger.info(f"Queueing questions for caching: {subject} at {level_key} (MongoDB level: {mongo_level})")
        processed_papers_metadata = []
            
        try:
            client = MongoDBClient()
            documents = client.get_questions_by_subject_level(subject, mongo_level, limit=50)
            self.logger.info(f"Found {len(documents)} source documents to process for {subject} at {level_key}")
            
            if not documents:
                self.logger.warning(f"No source documents found for {subject} at {mongo_level} level")
                self._update_global_subject_metadata(subject, level_key, [])
                return
            
            # Create base cache directories (ensure paths are correct)
            safe_subject = self._safe_filename(subject)
            safe_level = self._safe_filename(level_key)
            level_dir = os.path.join(self.QUESTIONS_DIR, safe_subject, safe_level)
            answers_base_dir = os.path.join(self.CACHE_DIR, "answers", safe_subject, safe_level)
            os.makedirs(level_dir, exist_ok=True)
            os.makedirs(answers_base_dir, exist_ok=True)

            # Process each source document (paper)
            for doc_index, doc in enumerate(documents): # Use enumerate for logging context
                doc_question_count = 0
                doc_valid_image_url_count = 0 # Count valid URLs found in this doc
                doc_downloaded_image_count = 0 # Count successfully downloaded images for this doc

                safe_doc = self._mongo_to_json_serializable(doc)
                mongo_doc_id = str(safe_doc.get('_id', f'missing_id_{doc_index}'))
                self.logger.debug(f"Processing source document #{doc_index} (ID: {mongo_doc_id})")

                # Extract Parent Document Metadata
                source_document_id = safe_doc.get('document_id')
                source_file_id = safe_doc.get('file_id')
                source_file_name = safe_doc.get('file_name')

                paper_meta = safe_doc.get('paper_meta', {})
                year = str(paper_meta.get('Year', 'Unknown'))
                term_raw = paper_meta.get('Term')
                term = term_raw if term_raw else 'Unknown'
                paper_number = str(paper_meta.get('PaperNumber', 'Unknown'))
                
                # Create year directories
                year_dir = os.path.join(level_dir, year)
                year_answers_dir = os.path.join(answers_base_dir, year)
                os.makedirs(year_dir, exist_ok=True)
                os.makedirs(year_answers_dir, exist_ok=True)
                
                if 'questions' not in safe_doc or not isinstance(safe_doc['questions'], list):
                     self.logger.warning(f"Source document {mongo_doc_id} has missing/invalid 'questions' array. Skipping.")
                     continue

                processed_questions_for_doc = [] # Hold updated questions for this doc before modifying original

                # Process each individual question within the document
                for question_index, question in enumerate(safe_doc.get('questions',[])):
                    if not isinstance(question, dict):
                        self.logger.warning(f"Skipping invalid question item #{question_index} (not a dict) in doc {mongo_doc_id}")
                        processed_questions_for_doc.append(question) # Keep original invalid item maybe? Or skip?
                        continue

                    # Extract question number (ensure this logic assigns question_number_str)
                        q_num = question.get('question_number')
                        if isinstance(q_num, dict) and '$numberInt' in q_num:
                            question_number_str = str(q_num['$numberInt'])
                        else:
                            question_number_str = str(q_num) if q_num is not None else f"idx{question_index}"
                    # --- Ensure question_number_str is now assigned ---

                    # --- Image Processing ---
                    processed_images = []
                    original_images = question.get('images', [])

                    # --- FIX: Move Log before the inner loop ---
                    # Log that we are starting image processing for this specific question number
                    if original_images and isinstance(original_images, list):
                         self.logger.debug(f"Processing {len(original_images)} image entries for q#{question_number_str} in doc {mongo_doc_id}") 
                         # --- End FIX ---

                         for i, img_info in enumerate(original_images):
                             local_path = None
                             updated_img_info = img_info.copy()

                             if isinstance(img_info, dict) and 'url' in img_info:
                                 img_url = img_info.get('url')
                                 img_label = img_info.get('label')

                                 # Check if URL *looks* valid before attempting download helper
                                 if img_url and isinstance(img_url, str) and img_url.startswith(('http://', 'https://')):
                                     doc_valid_image_url_count += 1
                                     # --- CALL THE CORRECTED HELPER ---
                                     local_path = self._download_and_save_asset(
                                         img_url, subject, level_key, year,
                                         question_number_str, i, img_label
                                     )
                                     # --- Store the result ---
                                     updated_img_info['local_path'] = local_path # Add/update local_path key
                                     if local_path:
                                         doc_downloaded_image_count += 1 # Increment success count
                                 else:
                                     # Log skipping due to invalid URL format found in data
                                     self.logger.info(f"q#{question_number_str} img#{i}: No valid image URL specified (URL is '{img_url}'). Skipping download.")
                                     updated_img_info['local_path'] = None # Ensure it's None if skipped
                             else:
                                 # Log skipping due to invalid image entry structure
                                 self.logger.warning(f"q#{question_number_str} img#{i}: Invalid image entry structure. Skipping. Entry: {img_info}")
                                 updated_img_info['local_path'] = None # Ensure it's None if skipped

                             processed_images.append(updated_img_info) # Add updated dict to list
                    else:
                         # Log if no images list found for this question
                         self.logger.debug(f"No 'images' list found or list is empty for q#{question_number_str}.")
                    # --- End Image Processing ---

                    # Prepare the final question data object for JSON saving
                    # Create a new dict to avoid modifying the original 'question' dict in place
                    question_data_to_save = {
                        "id": mongo_doc_id, # Link back to original document
                            "subject": subject,
                            "level": level_key,
                            "year": year,
                        "question_number_str": question_number_str, # Processed string version
                        # Copy other relevant fields from original question dict
                        "question_text": question.get("question_text", ""),
                        "topic": question.get("topic"),
                        "subtopic": question.get("subtopic"),
                        "difficulty": question.get("difficulty"),
                        "context_materials": question.get("context_materials"),
                        "sub_questions": question.get("sub_questions"),
                        "tables": question.get("tables"),
                        "marks": question.get("marks"),
                        # Use the processed images list
                        "images": processed_images,
                        "answer_ref": f"{question_number_str}.json" # Example if answers are separate
                        # Avoid adding 'original_question' back into itself if not needed
                    }


                    # Save the question JSON file
                    question_filename = os.path.join(year_dir, f"{question_number_str}.json")
                    try:
                        with open(question_filename, 'w', encoding='utf-8') as f:
                            json.dump(question_data_to_save, f, ensure_ascii=False, indent=4) # Use indent 4 maybe
                        doc_question_count += 1
                    except Exception as e:
                         self.logger.error(f"Failed to save question file {question_filename}: {e}", exc_info=True)


                    # --- Process and save the corresponding answer ---
                    # Make sure this logic uses 'year_answers_dir'
                    # ... (existing answer fetching/saving logic) ...

                # --- Store metadata for this paper ---
                paper_metadata = {
                    "mongo_doc_id": mongo_doc_id,
                    "source_document_id": source_document_id,
                    "source_file_id": source_file_id,
                    "source_file_name": source_file_name,
                                "year": year,
                    "term": term,
                    "paper_number": paper_number,
                    "question_count": doc_question_count,
                    "image_url_count": doc_valid_image_url_count, # Total valid URLs found
                    "image_download_count": doc_downloaded_image_count # Total actually downloaded
                }
                processed_papers_metadata.append(paper_metadata)
                self.logger.debug(f"Collected metadata for paper {mongo_doc_id} ({source_file_name}): {doc_question_count} questions, {doc_valid_image_url_count} valid URLs, {doc_downloaded_image_count} images downloaded.")

            # --- After processing all documents ---
            self.logger.info(f"Finished processing all documents for {subject}/{level_key}.")
            self._update_global_subject_metadata(subject, level_key, processed_papers_metadata)

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
        Retrieves a random, unanswered cached question for the application's user
        for the given subject and level from the JSON file cache.
        """
        logger.info(f"Attempting to get random unanswered question for {subject_name}/{level_key}")
        potential_question_files = []
        answered_question_ids = set()

        # 1. Find all potential question JSON files
        try:
            subject_safe_name = self._safe_filename(subject_name)
            level_path = os.path.join(self.QUESTIONS_DIR, subject_safe_name, level_key)
            logger.debug(f"Looking for questions in: {level_path}")

            if not os.path.isdir(level_path):
                logger.warning(f"Cache directory does not exist: {level_path}")
                return None

            for year_dir in os.listdir(level_path):
                year_path = os.path.join(level_path, year_dir)
                if os.path.isdir(year_path):
                    for filename in os.listdir(year_path):
                        if filename.endswith(".json"):
                            potential_question_files.append(os.path.join(year_path, filename))

            if not potential_question_files:
                logger.warning(f"No question files found in {level_path}")
                return None
            logger.debug(f"Found {len(potential_question_files)} potential question files.")

        except OSError as e:
            logger.error(f"Error accessing cache directory {level_path}: {e}")
            return None

        # 2. Get IDs of all answered questions (since it's a single-user app)
        try:
            with get_db_session() as session:
                logger.debug("Querying database for answered questions...")
                answered_responses = session.query(QuestionResponse.cached_question_id)\
                    .join(ExamResult) \
                    .filter(QuestionResponse.cached_question_id.isnot(None))\
                    .distinct()\
                    .all()
                answered_question_ids = {resp[0] for resp in answered_responses}
                logger.debug(f"Found {len(answered_question_ids)} distinct answered cached questions in the database.")

        except Exception as e:
            logger.error(f"Error querying answered questions from database: {e}", exc_info=True)
            logger.warning("Proceeding without filtering answered questions due to DB error.")
            answered_question_ids = set()

        # 3. Filter out answered questions
        unanswered_question_files = []
        for file_path in potential_question_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    question_data = json.load(f)
                    question_id = question_data.get('id')
                    if question_id and question_id in answered_question_ids:
                        logger.debug(f"Skipping answered question: {file_path} (ID: {question_id})")
                        continue
                    unanswered_question_files.append(file_path)
            except json.JSONDecodeError:
                logger.warning(f"Could not decode JSON from file: {file_path}")
            except KeyError:
                logger.warning(f"Could not find 'id' field in question JSON: {file_path}")
            except Exception as e:
                logger.error(f"Error processing question file {file_path}: {e}")

        logger.debug(f"Found {len(unanswered_question_files)} unanswered question files.")

        # 4. Select a random unanswered question
        if not unanswered_question_files:
            logger.warning(f"No unanswered questions available for {subject_name}/{level_key}")
            return None

        selected_file_path = random.choice(unanswered_question_files)
        logger.info(f"Selected random question file: {selected_file_path}")

        # 5. Load and return its data
        try:
            # Check if file exists
            if not os.path.exists(selected_file_path):
                logger.error(f"File does not exist at path: {selected_file_path}")
                return None
            
            # Log file size and last modified time
            file_stats = os.stat(selected_file_path)
            logger.info(f"File exists - Size: {file_stats.st_size} bytes, Modified: {datetime.fromtimestamp(file_stats.st_mtime)}")
            
            # Try to read raw contents first
            with open(selected_file_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
                logger.info(f"Raw file contents: {raw_content}")
                
                final_question_data = json.loads(raw_content)
                return final_question_data
        except Exception as e:
            logger.error(f"Failed to load selected question file {selected_file_path}: {e}", exc_info=True)
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
        # ... (Implementation of this method should already exist) ...
        pass
