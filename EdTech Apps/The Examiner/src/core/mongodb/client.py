import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import backoff
import logging
from typing import Dict, List, Optional, Any, Union
import os
import json
from datetime import datetime
import re
import time

# Import our credential manager
from .credential_manager import CredentialManager
from src.core.firebase.client import FirebaseClient

# Set up logging
logger = logging.getLogger(__name__)

class SubscriptionRequiredError(Exception):
    """Error raised when a subscription is required but user isn't subscribed"""
    pass

class MongoDBClient:
    """
    Client for connecting to MongoDB and retrieving exam questions.
    Implements connection pooling, retry logic, and standardization of fields.
    """
    _instance = None
    
    # MongoDB connection settings
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    
    # Hardcoded read-only credentials
    MONGODB_URI = "mongodb+srv://Examiner:examiner12@adalchemyai.q3tzkok.mongodb.net/"
    DB_NAME = "fundaAI"
    
    # Term mapping
    TERM_MAPPING = {
        # Term 1 (January to June)
        "January": "Term 1",
        "February/March": "Term 1",
        "April": "Term 1", 
        "May/June": "Term 1",
        # Term 2 (July to December)
        "October": "Term 2",
        "Oct/Nov": "Term 2",
        "October/November": "Term 2"
    }
    
    # Subject standardization mapping
    SUBJECT_MAPPING = {
        "ACCOUNTING": "Accounting",
        "ADDITIONAL MATHEMATICS": "Additional Mathematics",
        "BIOLOGY": "Biology",
        "COMPUTER SCIENCE": "Computer Science",
        "ECONOMICS": "Economics",
        "ENGLISH LANGUAGE": "English Language",
        "ENGLISHLANGUAGE": "English Language",
        "HISTORY": "History",
        "Mathematics": "Mathematics",
        "Physics": "Physics",
        "Science": "Science"
    }
    
    # Valid subscription types
    VALID_SUBSCRIPTION_TYPES = ["trial", "annual", "monthly"]
    
    def __new__(cls):
        """Singleton pattern to ensure only one instance exists"""
        if cls._instance is None:
            cls._instance = super(MongoDBClient, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the MongoDB client"""
        if self.initialized:
            return
            
        self.client = None
        self.db = None
        self.connected = False
        self.credential_manager = None  # We won't need this anymore with hardcoded credentials
        
        # Initialize connection
        self.connect()
        
        self.initialized = True
        logger.info("MongoDB client initialized")
    
    def _load_credentials(self):
        """
        Load MongoDB credentials - now using hardcoded values
        
        Returns:
            tuple: (uri, db_name) for MongoDB connection
        """
        return (self.MONGODB_URI, self.DB_NAME)
    
    def setup_credentials(self, uri: str, db_name: str) -> bool:
        """
        For backwards compatibility - no longer needed with hardcoded credentials
        
        Returns:
            bool: True (always successful since using hardcoded)
        """
        logger.info("Using hardcoded read-only MongoDB credentials")
        return True
    
    def has_credentials(self) -> bool:
        """
        Check if MongoDB credentials are available
        
        Returns:
            bool: True (always available with hardcoded credentials)
        """
        return True
    
    @backoff.on_exception(backoff.expo, 
                     (ConnectionFailure, ServerSelectionTimeoutError),
                     max_tries=5)
    def connect(self, force=False) -> bool:
        """
        Connect to MongoDB with subscription verification
        
        Args:
            force: Force reconnection even if already connected
            
        Returns:
            bool: True if connected successfully
        """
        # Check subscription status first
        if not self._check_subscription():
            logger.warning("Cannot connect to MongoDB - subscription inactive")
            return False
            
        # Don't reconnect if already connected
        if self.connected and not force:
            return True
            
        try:
            # Load credentials
            uri, db_name = self._load_credentials()
            
            # Connect to MongoDB
            self.client = MongoClient(
                uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=30000,
                maxPoolSize=10
            )
            
            # Test connection
            self.client.admin.command('ping')
            
            # Set database
            self.db = self.client[db_name]
            
            logger.info(f"Connected to MongoDB database: {db_name}")
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("Disconnected from MongoDB")
    
    def _ensure_connected(self) -> bool:
        """Ensure we're connected to MongoDB with active subscription"""
        # First check subscription
        if not self._check_subscription():
            raise SubscriptionRequiredError("Active subscription required to access content")
            
        if not self.connected:
            return self.connect()
        return True
    
    def _standardize_subject(self, subject: str) -> str:
        """Standardize subject name for consistent matching"""
        # Look up in our mapping
        standardized = self.SUBJECT_MAPPING.get(subject)
        if standardized:
            return standardized
            
        # If not in mapping, return as is with proper capitalization
        return subject.title()
    
    def _standardize_level(self, level: str) -> str:
        """Standardize level name for consistent matching"""
        level_lower = level.lower()
        if "primary" in level_lower:
            return "Primary School"
        elif "olevel" in level_lower or "o level" in level_lower:
            return "OLevel"
        elif "aslevel" in level_lower or "as level" in level_lower:
            return "ASLevel"
        return level
    
    def _standardize_term(self, term: str) -> str:
        """Convert specific term names to Term 1 or Term 2"""
        return self.TERM_MAPPING.get(term, term)
    
    def get_questions_by_subject_level(self, subject: str, level: str, 
                                   limit: int = 50, year: Optional[str] = None) -> List[Dict]:
        """
        Get questions for a specific subject and level
        
        Args:
            subject: Subject name
            level: Level (Primary School, OLevel, ASLevel)
            limit: Maximum number of questions to return
            year: Optional filter by year
            
        Returns:
            List of question documents
        """
        try:
            # First verify subscription and connection
            if not self._ensure_connected():
                return []
                
            # Standardize inputs for consistent querying
            std_subject = self._standardize_subject(subject)
            std_level = self._standardize_level(level)
            
            # Build query
            query = {
                "subject": {"$regex": f"^{std_subject}$", "$options": "i"},
                "level": {"$regex": f"^{std_level}$", "$options": "i"}
            }
            
            # Add year filter if provided
            if year:
                query["Year"] = year
                
            # Get questions collection
            questions_collection = self.db["extracted-questions"]
            
            # Execute query
            cursor = questions_collection.find(query).limit(limit)
            
            # Process results
            results = []
            for doc in cursor:
                # Process document
                self._process_document_id(doc)
                results.append(doc)
                
            logger.info(f"Retrieved {len(results)} questions for {std_subject} at {std_level} level")
            return results
            
        except SubscriptionRequiredError as e:
            logger.warning(f"Subscription error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error retrieving questions by subject/level: {e}")
            return []
    
    def get_questions_by_topic(self, subject: str, topic: str, limit: int = 50) -> List[Dict]:
        """
        Get questions for a specific subject and topic
        
        Args:
            subject: Subject name
            topic: Topic name
            limit: Maximum number of questions to return
            
        Returns:
            List of question documents
        """
        try:
            # First verify subscription and connection
            if not self._ensure_connected():
                return []
                
            # Standardize subject
            std_subject = self._standardize_subject(subject)
            
            # Build query
            query = {
                "subject": {"$regex": f"^{std_subject}$", "$options": "i"},
                "topic": {"$regex": f".*{topic}.*", "$options": "i"}
            }
                
            # Get questions collection
            questions_collection = self.db["extracted-questions"]
            
            # Execute query
            cursor = questions_collection.find(query).limit(limit)
            
            # Process results
            results = []
            for doc in cursor:
                # Process document
                self._process_document_id(doc)
                results.append(doc)
                
            logger.info(f"Retrieved {len(results)} questions for {std_subject} on topic '{topic}'")
            return results
            
        except SubscriptionRequiredError as e:
            logger.warning(f"Subscription error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error retrieving questions by topic: {e}")
            return []
    
    def get_matching_answer(self, question_doc: Dict) -> Optional[Dict]:
        """
        Find the matching answer for a question document
        
        Args:
            question_doc: The question document
            
        Returns:
            Matching answer document or None if not found
        """
        try:
            # First verify subscription and connection
            if not self._ensure_connected():
                return None
                
            # Extract matching fields
            subject = question_doc.get("subject")
            level = question_doc.get("level")
            year = question_doc.get("Year")
            paper = question_doc.get("Paper", {}).get("$numberInt")
            term = self._standardize_term(question_doc.get("Term"))
            question_number = question_doc.get("question_number", {}).get("$numberInt")
            
            if not all([subject, level, year, paper, term, question_number]):
                logger.warning("Missing required fields for answer matching")
                return None
                
            # Build query to find matching answer
            query = {
                "subject": {"$regex": f"^{subject}$", "$options": "i"},
                "level": {"$regex": f"^{level}$", "$options": "i"},
                "Year": year,
                "Paper.$numberInt": paper,
                "Term": {"$regex": f".*{term}.*", "$options": "i"},
                "question_number.$numberInt": question_number
            }
                
            # Get answers collection
            answers_collection = self.db["extracted-answers"]
            
            # Execute query
            answer_doc = answers_collection.find_one(query)
            
            if answer_doc:
                self._process_document_id(answer_doc)
                logger.info(f"Found matching answer for question {question_number} in {subject} {level} {year}")
                return answer_doc
            else:
                logger.warning(f"No matching answer found for question {question_number} in {subject} {level} {year}")
                return None
                
        except SubscriptionRequiredError as e:
            logger.warning(f"Subscription error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving matching answer: {e}")
            return None
    
    def get_available_subjects(self) -> List[str]:
        """
        Get list of available subjects in the database
        
        Returns:
            List of unique subjects
        """
        try:
            # First verify subscription and connection
            if not self._ensure_connected():
                return []
                
            # Get questions collection
            questions_collection = self.db["extracted-questions"]
            
            # Get distinct subjects
            subjects = questions_collection.distinct("subject")
            
            # Standardize and deduplicate
            standardized_subjects = set()
            for subject in subjects:
                std_subject = self._standardize_subject(subject)
                standardized_subjects.add(std_subject)
                
            return sorted(list(standardized_subjects))
            
        except SubscriptionRequiredError as e:
            logger.warning(f"Subscription error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error retrieving available subjects: {e}")
            return []
    
    def get_available_levels(self) -> List[str]:
        """
        Get list of available levels in the database
        
        Returns:
            List of unique levels
        """
        try:
            # First verify subscription and connection
            if not self._ensure_connected():
                return []
                
            # Get questions collection
            questions_collection = self.db["extracted-questions"]
            
            # Get distinct levels
            levels = questions_collection.distinct("level")
            
            # Standardize and deduplicate
            standardized_levels = set()
            for level in levels:
                std_level = self._standardize_level(level)
                standardized_levels.add(std_level)
                
            return sorted(list(standardized_levels))
            
        except SubscriptionRequiredError as e:
            logger.warning(f"Subscription error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error retrieving available levels: {e}")
            return []
    
    def _process_document_id(self, doc: Dict):
        """Convert MongoDB _id to string format for JSON compatibility"""
        if '_id' in doc:
            doc['_id'] = str(doc['_id'])
        return doc
    
    def _check_subscription(self) -> bool:
        """
        Verify user has active subscription before allowing MongoDB access
        
        Returns:
            bool: True if subscription is active or in grace period
        """
        try:
            # Get subscription status from Firebase
            firebase = FirebaseClient()
            user_doc = firebase.check_subscription_status()
            
            # Debug logging to see full document structure
            logger.debug(f"Full user document: {user_doc}")
            
            # CRITICAL FIX: The document might be in one of two formats:
            # 1. Direct Firestore format with fields at the top level
            # 2. Nested format with fields inside a 'fields' key
            
            # First, try to extract fields if they're in a nested structure
            if 'fields' in user_doc:
                fields = user_doc['fields']
            else:
                # If 'fields' key doesn't exist, assume the document itself contains the fields
                fields = user_doc
                
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
            
            # If we don't have a subscription type, we can't verify
            if not subscription_type:
                logger.warning("No subscription type found in user document")
                return False
                
            # Parse expiration date
            sub_end_date = None
            try:
                if sub_end_str:
                    sub_end_date = datetime.fromisoformat(sub_end_str)
                    logger.debug(f"Parsed end date: {sub_end_date}")
            except ValueError as e:
                logger.error(f"Invalid date format for subscription end: {sub_end_str} - {e}")
            
            # Check subscription validity
            current_date = datetime.now()
            logger.debug(f"Current date: {current_date}")
            
            # First, check if the subscription type is valid
            if subscription_type not in self.VALID_SUBSCRIPTION_TYPES:
                logger.warning(f"Invalid subscription type: {subscription_type}")
                return False
            
            # Next, check if the subscription is expired
            if sub_end_date and current_date > sub_end_date:
                logger.warning(f"Subscription expired on {sub_end_date.isoformat()}")
                return False
            
            # If we get here, the subscription is valid
            logger.info(f"Subscription is active: Type={subscription_type}, Expires={sub_end_date}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking subscription status: {e}", exc_info=True)
            
            # If error occurs during verification, default to allowing access
            # This prevents users from being locked out due to network issues
            logger.info("Error during subscription check - allowing access by default")
            return True 