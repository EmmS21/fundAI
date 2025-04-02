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
        if self.initialized:
            return
            
        # Create cache directories if they don't exist
        os.makedirs(self.METADATA_DIR, exist_ok=True)
        os.makedirs(self.ASSETS_DIR, exist_ok=True)
        os.makedirs(self.QUESTIONS_DIR, exist_ok=True)
        
        self.mongodb_client = MongoDBClient()
        
        # Network monitor for connection status
        self.network_monitor = NetworkMonitor()
        
        # Thread control
        self.running = False
        self.thread = None
        
        # Subscription cache
        self.subscription_cache = None
        self.subscription_cache_time = 0
        
        # Ensure required tables exist
        self._ensure_tables()
        
        # Initialize database connection and structure
        self.db_path = os.path.join(os.path.dirname(__file__), self.DB_FILE)
        self.conn = None
        self.lock = threading.RLock()  # Reentrant lock for thread safety
        
        # Set default TTL values (in seconds)
        self.ttl_fresh = 3600  # 1 hour
        self.ttl_stale = 86400  # 24 hours
        
        # We don't manually register in services registry anymore
        # Services.py will handle this by importing us
        
        self._initialize_db()
        self.initialized = True
        logger.info("Cache Manager initialized")
    
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
        try:
            logger.info(f"Queueing questions for caching: {subject} at {level_key} (MongoDB level: {mongo_level})")
            
            # Get MongoDB client
            from src.core.mongodb.client import MongoDBClient
            client = MongoDBClient()
            
            # Fetch documents for the subject and level
            documents = client.get_questions_by_subject_level(subject, mongo_level, limit=50)
            logger.info(f"Found {len(documents)} question documents to cache for {subject} at {level_key}")
            
            if not documents:
                logger.warning(f"No questions found for {subject} at {mongo_level} level")
                return
            
            # Create directories
            subject_dir = os.path.join(self.QUESTIONS_DIR, subject)
            answers_dir = os.path.join(self.CACHE_DIR, "answers", subject)
            
            os.makedirs(subject_dir, exist_ok=True)
            os.makedirs(answers_dir, exist_ok=True)
            
            level_dir = os.path.join(subject_dir, level_key)
            level_answers_dir = os.path.join(answers_dir, level_key)
            
            os.makedirs(level_dir, exist_ok=True)
            os.makedirs(level_answers_dir, exist_ok=True)
            
            # Track progress
            saved_questions = 0
            saved_answers = 0
            
            # Process each document
            for doc in documents:
                # First, convert MongoDB-specific types
                safe_doc = self._mongo_to_json_serializable(doc)
                
                # Extract document ID
                doc_id = str(doc.get('_id', str(uuid.uuid4())))
                
                # Extract year from document
                paper_meta = doc.get('paper_meta', {})
                year = str(paper_meta.get('Year', datetime.now().year))
                
                # Create year directories
                year_dir = os.path.join(level_dir, year)
                year_answers_dir = os.path.join(level_answers_dir, year)
                
                os.makedirs(year_dir, exist_ok=True)
                os.makedirs(year_answers_dir, exist_ok=True)
                
                # MAIN FIX: Extract individual questions from the 'questions' array
                if 'questions' in doc and isinstance(doc['questions'], list):
                    logger.info(f"Found {len(doc['questions'])} individual questions in document {doc_id}")
                    
                    # Process each question in the array
                    for question in doc['questions']:
                        # Extract question number
                        q_num = question.get('question_number')
                        if isinstance(q_num, dict) and '$numberInt' in q_num:
                            question_number = q_num['$numberInt']
                        else:
                            question_number = str(q_num) if q_num is not None else str(saved_questions + 1)
                            
                        # Extract question text
                        question_text = question.get('question_text', '')
                        
                        # Get matching answer
                        answer_doc = client.get_matching_answer(doc)
                        
                        # Filenames
                        question_filename = os.path.join(year_dir, f"{question_number}.json")
                        answer_filename = os.path.join(year_answers_dir, f"{question_number}.json")
                        
                        # Extract and save images
                        local_images = []
                        if 'images' in question and isinstance(question['images'], list):
                            for i, img in enumerate(question['images']):
                                if 'url' in img:
                                    try:
                                        img_url = img['url']
                                        img_data = requests.get(img_url, timeout=10).content
                                        img_filename = f"{question_number}_img_{i}.jpg"
                                        img_path = os.path.join(year_dir, img_filename)
                                        
                                        with open(img_path, 'wb') as f:
                                            f.write(img_data)
                                        
                                        local_images.append(img_filename)
                                        logger.debug(f"Saved image {img_url} to {img_path}")
                                    except Exception as e:
                                        logger.error(f"Error saving image {img_url}: {e}")
                        
                        # Safe-serialize the question
                        question_safe = self._mongo_to_json_serializable(question)
                        
                        # Create question data object
                        question_data = {
                            "id": doc_id,
                            "subject": subject,
                            "level": level_key,
                            "year": year,
                            "question_number": question_number,
                            "text": question_text,
                            "images": local_images,
                            "original_question": question_safe,
                            "answer_ref": f"{question_number}.json" if answer_doc else None
                        }
                        
                        # Save the question file
                        with open(question_filename, 'w', encoding='utf-8') as f:
                            json.dump(question_data, f, ensure_ascii=False, indent=2)
                        saved_questions += 1
                        
                        # Save the answer if available
                        if answer_doc:
                            # Convert answer to safe format
                            answer_safe = self._mongo_to_json_serializable(answer_doc)
                            
                            # Try to find matching answer for this question
                            answer_text = None
                            
                            # First check in answers array
                            if 'answers' in answer_doc and isinstance(answer_doc['answers'], list):
                                for ans in answer_doc['answers']:
                                    ans_num = ans.get('question_number')
                                    if isinstance(ans_num, dict) and '$numberInt' in ans_num:
                                        ans_num = ans_num['$numberInt']
                                        
                                    if str(ans_num) == str(question_number):
                                        answer_text = ans.get('answer_text', '')
                                        if not answer_text:
                                            sub_answers = ans.get('sub_answers', [])
                                            if sub_answers:
                                                answer_text = "\n".join([sub.get('text', '') for sub in sub_answers])
                                        break
                            
                            # If not found, use whole document
                            if not answer_text:
                                answer_text = str(answer_safe)
                            
                            # Create answer data
                            answer_data = {
                                "id": str(answer_doc.get('_id', '')),
                                "question_id": doc_id,
                                "question_number": question_number,
                                "subject": subject,
                                "level": level_key,
                                "year": year,
                                "text": answer_text,
                                "original_answer": answer_safe
                            }
                            
                            # Save the answer file
                            with open(answer_filename, 'w', encoding='utf-8') as f:
                                json.dump(answer_data, f, ensure_ascii=False, indent=2)
                            saved_answers += 1
                else:
                    # Handle documents that don't have a questions array
                    logger.warning(f"Document {doc_id} doesn't have a questions array, treating as single question")
                    
                    # Use document ID as question number if not available
                    question_number = "1"  # Default question number
                    
                    # Find text directly in document
                    question_text = doc.get('question_text', doc.get('text', str(doc)))
                    
                    # Get matching answer
                    answer_doc = client.get_matching_answer(doc)
                    
                    # Filenames
                    question_filename = os.path.join(year_dir, f"{question_number}.json")
                    answer_filename = os.path.join(year_answers_dir, f"{question_number}.json")
                    
                    # Create question data
                    question_data = {
                        "id": doc_id,
                        "subject": subject,
                        "level": level_key,
                        "year": year,
                        "question_number": question_number,
                        "text": question_text,
                        "original_document": safe_doc,
                        "answer_ref": f"{question_number}.json" if answer_doc else None
                    }
                    
                    # Save the question
                    with open(question_filename, 'w', encoding='utf-8') as f:
                        json.dump(question_data, f, ensure_ascii=False, indent=2)
                    saved_questions += 1
                    
                    # Save answer if available
                    if answer_doc:
                        answer_safe = self._mongo_to_json_serializable(answer_doc)
                        answer_text = answer_doc.get('answer_text', str(answer_doc))
                        
                        answer_data = {
                            "id": str(answer_doc.get('_id', '')),
                            "question_id": doc_id,
                            "subject": subject,
                            "level": level_key,
                            "year": year,
                            "question_number": question_number,
                            "text": answer_text,
                            "original_answer": answer_safe
                        }
                        
                        with open(answer_filename, 'w', encoding='utf-8') as f:
                            json.dump(answer_data, f, ensure_ascii=False, indent=2)
                        saved_answers += 1
            
            # Update subject cache metadata
            self._update_subject_cache_metadata(subject, level_key)
            
            logger.info(f"Successfully saved {saved_questions} questions and {saved_answers} answers for {subject} at {level_key}")
            
        except Exception as e:
            logger.error(f"Error queueing questions for caching: {e}", exc_info=True)
    
    def _extract_year_from_question(self, question: Dict) -> Optional[str]:
        """Extract year from question document"""
        # Try to get year from paper_meta
        paper_meta = question.get('paper_meta', {})
        year = paper_meta.get('Year')
        
        # If not found, try to extract from Paper field
        if not year:
            paper = paper_meta.get('Paper', '')
            # Try to extract year from paper string (looking for 4 digit numbers)
            year_match = re.search(r'20\d{2}', paper)
            if year_match:
                year = year_match.group(0)
        
        return str(year) if year else None
    
    def _save_question_assets(self, question: Dict, doc_id: str, subject: str, level: str, 
                             year: str, question_number: str) -> List[str]:
        """Save question assets (images, tables) to the cache"""
        saved_assets = []
        
        # Create assets directory if needed
        asset_dir = os.path.join(self.ASSETS_DIR, self._safe_filename(subject), level, year, question_number)
        os.makedirs(asset_dir, exist_ok=True)
        
        # Process images
        if 'images' in question and question['images']:
            for i, image in enumerate(question['images']):
                try:
                    if 'url' in image:
                        # Get image URL
                        image_url = image['url']
                        
                        # Hash URL to create a filename
                        filename = f"{self._hash_url(image_url)}.jpg"
                        file_path = os.path.join(asset_dir, filename)
                        
                        # Check if we already have this asset
                        if os.path.exists(file_path):
                            logger.debug(f"Asset already exists: {file_path}")
                        else:
                            # Download the image
                            response = requests.get(image_url, timeout=30)
                            if response.status_code == 200:
                                with open(file_path, 'wb') as f:
                                    f.write(response.content)
                                logger.info(f"Downloaded asset from {image_url} to {file_path}")
                            else:
                                logger.warning(f"Failed to download asset from {image_url}: {response.status_code}")
                                continue
                        
                        # Update the URL to point to our local copy
                        question['images'][i]['url'] = file_path
                        saved_assets.append(file_path)
                except Exception as e:
                    logger.error(f"Error saving asset: {e}")
        
        return saved_assets
    
    def _update_subject_cache_metadata(self, subject: str, level: str):
        """Update metadata for a subject/level combo"""
        try:
            # Get metadata path
            metadata_path = os.path.join(self.METADATA_DIR, 'subjects.json')
            
            # Create default metadata
            metadata = {}
            
            # Load existing metadata if available
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            
            # Ensure subject exists
            if subject not in metadata:
                metadata[subject] = {}
                
            # Update level metadata
            if level not in metadata[subject]:
                metadata[subject][level] = {}
                
            # Update last updated timestamp
            metadata[subject][level]['last_updated'] = time.time()
            
            # Count questions
            subject_dir = os.path.join(self.QUESTIONS_DIR, self._safe_filename(subject), level)
            if os.path.exists(subject_dir):
                # Count years (subdirectories)
                years = [d for d in os.listdir(subject_dir) if os.path.isdir(os.path.join(subject_dir, d))]
                metadata[subject][level]['years'] = years
                
                # Count total questions
                question_count = 0
                for year in years:
                    year_dir = os.path.join(subject_dir, year)
                    question_files = [f for f in os.listdir(year_dir) if f.endswith('.json')]
                    question_count += len(question_files)
                
                metadata[subject][level]['question_count'] = question_count
            
            # Save metadata
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
                
            logger.info(f"Updated cache metadata for {subject}/{level}: {metadata[subject][level]}")
            
        except Exception as e:
            logger.error(f"Error updating subject cache metadata: {e}")
    
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

        Args:
            subject_name: The name of the subject.
            level_key: The level identifier (e.g., 'o_level').

        Returns:
            A dictionary containing the question data (loaded from JSON)
            or None if no unanswered questions are found or an error occurs.
        """
        logger.info(f"Attempting to get random unanswered question for {subject_name}/{level_key}")
        potential_question_files = []
        answered_question_ids = set()

        # 1. Find all potential question JSON files
        try:
            subject_safe_name = self._safe_filename(subject_name)
            level_path = os.path.join(self.QUESTIONS_DIR, subject_safe_name, level_key)

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
                # Query QuestionResponse directly for all distinct cached_question_ids that have been answered.
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
            with open(selected_file_path, 'r', encoding='utf-8') as f:
                final_question_data = json.load(f)
            # TODO: Add any necessary post-processing like resolving image paths if stored relatively.
            return final_question_data
        except Exception as e:
            logger.error(f"Failed to load selected question file {selected_file_path}: {e}", exc_info=True)
            return None
