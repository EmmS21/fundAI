from src.data.database.operations import PaperCacheOperations, UserOperations
from src.utils.db import get_db_session
from typing import Any, List, Dict, Optional
import threading
import time
import os
import json
import logging
import sqlite3
from datetime import datetime, timedelta
import uuid
import requests
from PIL import Image
import hashlib
from src.core import services
from src.core.network.monitor import NetworkMonitor, NetworkStatus
from src.core.mongodb.client import MongoDBClient
from src.core.queue_manager import QueuePriority
from src.data.database.models import Base as BaseModel
from src.core.firebase.client import FirebaseClient

logger = logging.getLogger(__name__)

class CacheStatus:
    """Enumeration of cache statuses"""
    FRESH = "fresh"       
    STALE = "stale"        
    EXPIRED = "expired"   
    INVALID = "invalid"   

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
    PAPERS_PER_SUBJECT = 5   
    
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
        
        # Initialize MongoDB client
        self.mongodb_client = MongoDBClient()
        
        # Network monitor for connection status
        self.network_monitor = NetworkMonitor()
        
        # Thread control
        self.running = False
        self.thread = None
        
        # Ensure required tables exist
        self._ensure_tables()
        
        # Initialize database connection and structure
        self.db_path = os.path.join(os.path.dirname(__file__), self.DB_FILE)
        self.conn = None
        self.lock = threading.RLock()  # Reentrant lock for thread safety
        
        # Set default TTL values (in seconds)
        self.ttl_fresh = 3600  # 1 hour
        self.ttl_stale = 86400  # 24 hours
        
        # Register in services registry
        services.cache_manager = self
        
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
        """Check for new content that needs to be cached"""
        try:
            # Check subscription status first
            if not self._verify_subscription():
                print("Skipping content update - no active subscription")
                return
                
            # Get user subjects
            with get_db_session() as session:
                user = UserOperations.get_current_user()
                if not user:
                    print("No user found, skipping cache update")
                    return
                
                user_subjects = UserOperations.get_user_subjects(user.id)
                
            # For each subject, check if we need to cache more questions
            for subj in user_subjects:
                subject_name = subj['name']
                
                # Check which levels are enabled
                for level_key, enabled in subj['levels'].items():
                    if not enabled:
                        continue
                    
                    # Convert internal level key to MongoDB level format
                    mongo_level = self._convert_level_to_mongo_format(level_key)
                    
                    # Get number of cached questions for this subject/level
                    cached_count = self._get_cached_question_count(subject_name, level_key)
                    
                    # If we have fewer than threshold, cache more
                    if cached_count < 50:  # Aim for at least 50 questions per subject/level
                        self._queue_questions_for_caching(subject_name, level_key, mongo_level)
                
        except Exception as e:
            print(f"Error checking for updates: {e}")
    
    def _verify_subscription(self) -> bool:
        """
        Verify user has active subscription
        
        Returns:
            bool: True if subscription is active, False otherwise
        """
        try:
            # Get subscription status
            firebase = FirebaseClient()
            subscription = firebase.check_subscription_status()
            
            return subscription.get('is_active', False)
            
        except Exception as e:
            logger.error(f"Error verifying subscription: {e}")
            
            # For exceptions during verification, allow content access
            # (better user experience to show content than to block incorrectly)
            return True
    
    def _convert_level_to_mongo_format(self, level_key: str) -> str:
        """Convert internal level key to MongoDB level format"""
        level_mapping = {
            'grade_7': 'primary school',
            'o_level': 'olevel',
            'a_level': 'aslevel'
        }
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
    
    def _queue_questions_for_caching(self, subject: str, level_key: str, mongo_level: str):
        """Queue questions for download and caching"""
        try:
            # Skip if we're not connected to MongoDB
            if not self.mongodb_client.connected:
                logger.warning("Not connected to MongoDB, skipping question download")
                return
                
            # Get questions from MongoDB
            questions = self.mongodb_client.get_questions_by_subject_level(
                subject=subject,
                level=mongo_level,
                limit=30  # Fetch a batch of questions
            )
            
            if not questions:
                logger.info(f"No questions found for {subject} at {level_key} level")
                return
                
            logger.info(f"Queueing {len(questions)} questions for {subject} at {level_key} level")
            
            # Save each question to cache
            for question_doc in questions:
                self.save_question_from_mongodb(question_doc, subject, level_key)
                
        except Exception as e:
            logger.error(f"Error queueing questions: {e}")
    
    def save_question_from_mongodb(self, question_doc: Dict, subject: str, level: str) -> bool:
        """
        Save a MongoDB question document to the local cache.
        
        Args:
            question_doc: The MongoDB document containing questions
            subject: The subject name
            level: The level key (grade_7, o_level, a_level)
            
        Returns:
            bool: True if successful
        """
        try:
            # Extract document ID
            doc_id = question_doc.get('_id')
            if not doc_id:
                logger.error("Question document has no ID")
                return False
                
            # Extract paper metadata
            paper_meta = question_doc.get('paper_meta', {})
            year = paper_meta.get('Year', 'unknown')
            paper_number = paper_meta.get('Paper', {}).get('$numberInt', '1')
            term = paper_meta.get('Term', 'unknown')
            
            # Process each question in the document
            questions_list = question_doc.get('questions', [])
            if not questions_list:
                logger.warning(f"No questions found in document {doc_id}")
                return False
                
            # Create directory structure
            subject_dir = os.path.join(self.QUESTIONS_DIR, self._safe_filename(subject), level, year)
            os.makedirs(subject_dir, exist_ok=True)
            
            # Save each question
            for q_item in questions_list:
                question_number = q_item.get('question_number', {}).get('$numberInt', '0')
                if not question_number:
                    question_number = str(uuid.uuid4())[:8]  # Fallback ID if no number
                
                # Create filename
                filename = f"{year}_paper{paper_number}_q{question_number}.json"
                filepath = os.path.join(subject_dir, filename)
                
                # Save question data
                with open(filepath, 'w', encoding='utf-8') as f:
                    # Add metadata to help with retrieval
                    question_data = {
                        'doc_id': doc_id,
                        'subject': subject,
                        'level': level,
                        'year': year,
                        'paper': paper_number,
                        'term': term,
                        'question_number': question_number,
                        'data': q_item,
                        'cached_at': datetime.now().isoformat()
                    }
                    json.dump(question_data, f, ensure_ascii=False, indent=2)
                
                # Process and save images/assets
                self._save_question_assets(q_item, doc_id, subject, level, year, question_number)
                
            logger.info(f"Saved {len(questions_list)} questions from document {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving question from MongoDB: {e}")
            return False
    
    def _save_question_assets(self, question: Dict, doc_id: str, subject: str, level: str, 
                             year: str, question_number: str) -> List[str]:
        """
        Download and save assets (images, etc.) for a question.
        
        Returns:
            List of saved asset paths
        """
        saved_assets = []
        try:
            # Process images if present
            images = question.get('images', [])
            
            for idx, img_data in enumerate(images):
                # Get image URL
                img_url = img_data.get('url')
                if not img_url:
                    continue
                    
                # Create asset directory
                asset_dir = os.path.join(
                    self.ASSETS_DIR, 
                    self._safe_filename(subject), 
                    level, 
                    year, 
                    str(question_number)
                )
                os.makedirs(asset_dir, exist_ok=True)
                
                # Generate filename from URL
                filename = f"image_{idx}_{self._hash_url(img_url)}.jpg"
                filepath = os.path.join(asset_dir, filename)
                
                # Skip if already downloaded
                if os.path.exists(filepath):
                    saved_assets.append(filepath)
                    continue
                
                # Download image
                try:
                    if self.network_monitor.get_status() == NetworkStatus.ONLINE:
                        response = requests.get(img_url, timeout=10)
                        if response.status_code == 200:
                            # Save image
                            with open(filepath, 'wb') as f:
                                f.write(response.content)
                            
                            saved_assets.append(filepath)
                            logger.debug(f"Saved asset: {filepath}")
                except Exception as img_error:
                    logger.error(f"Error downloading image {img_url}: {img_error}")
            
            # Process any other assets here if needed
            
            return saved_assets
            
        except Exception as e:
            logger.error(f"Error saving question assets: {e}")
            return saved_assets
    
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
        # For cached content, we check subscription but don't strictly enforce it
        # This allows users to access content they've already downloaded
        subscription_active = self._verify_subscription()
        
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
            import random as rand
            selected_file = rand.choice(matching_files) if random else matching_files[0]
            
            # Load question data
            with open(selected_file, 'r', encoding='utf-8') as f:
                question_data = json.load(f)
                
            # Resolve asset paths
            self._resolve_asset_paths(question_data)
                
            # If we found content but subscription is expired, add warning
            if not subscription_active and question_data:
                question_data['subscription_expired'] = True
                
            return question_data
            
        except Exception as e:
            logger.error(f"Error getting cached question: {e}")
            return None
    
    def get_cached_questions_for_test(self, subject: str, level: str, 
                                     count: int = 10) -> List[Dict]:
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
                return []
                
            # Get all question files
            question_files = [f for f in os.listdir(year_path) if f.endswith('.json')]
            
            # Select randomly if we have more than we need
            import random as rand
            if len(question_files) > count:
                question_files = rand.sample(question_files, count)
            
            # Load each question
            for filename in question_files:
                filepath = os.path.join(year_path, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        question_data = json.load(f)
                        
                    # Resolve asset paths
                    self._resolve_asset_paths(question_data)
                    
                    questions.append(question_data)
                except Exception as file_error:
                    logger.error(f"Error loading question file {filepath}: {file_error}")
                    
            return questions
            
        except Exception as e:
            logger.error(f"Error getting questions from year: {e}")
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
