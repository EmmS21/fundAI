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
from bson import ObjectId

# Import our credential manager
from .credential_manager import CredentialManager
from src.core.firebase.client import FirebaseClient
from src.utils.hardware_identifier import HardwareIdentifier

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
    
    # Subject standardization mapping - expanded to handle more variations
    SUBJECT_MAPPING = {
        # All uppercase variations
        "ACCOUNTING": "Accounting",
        "ADDITIONAL MATHEMATICS": "Additional Mathematics",
        "BIOLOGY": "Biology",
        "COMPUTER SCIENCE": "Computer Science",
        "ECONOMICS": "Economics",
        "ENGLISH LANGUAGE": "English Language",
        "ENGLISHLANGUAGE": "English Language",
        "HISTORY": "History",
        
        # Title case variations
        "Accounting": "Accounting",
        "Additional Mathematics": "Additional Mathematics", 
        "Biology": "Biology",
        "Computer Science": "Computer Science",
        "Economics": "Economics",
        "English Language": "English Language",
        "History": "History",
        "Mathematics": "Mathematics",
        "Physics": "Physics",
        "Science": "Science"
    }
    
    # Level standardization mapping for both questions and answers
    QUESTION_LEVEL_MAPPING = {
        # Common variations for question documents
        "o level": "olevel",
        "olevel": "olevel",
        "O level": "olevel",
        "O Level": "olevel",
        "o_level": "olevel",
        "OLevel": "olevel",
        
        "a level": "aslevel",
        "A level": "aslevel",
        "A Level": "aslevel",
        "as level": "aslevel",
        "AS level": "aslevel",
        "AS Level": "aslevel",
        "aslevel": "aslevel",
        "a_level": "aslevel",
        "ASLevel": "aslevel",
        
        "primary": "primary school",
        "Primary": "primary school",
        "primary school": "primary school",
        "Primary School": "primary school",
        "grade_7": "primary school",
        "grade7": "primary school",
        "Grade 7": "primary school",
        "grade 7": "primary school"
    }
    
    ANSWER_LEVEL_MAPPING = {
        # Common variations for answer documents
        "o level": "OLevel",
        "olevel": "OLevel",
        "O level": "OLevel",
        "O Level": "OLevel",
        "o_level": "OLevel",
        "OLevel": "OLevel",
        
        "a level": "ASLevel",
        "A level": "ASLevel", 
        "A Level": "ASLevel",
        "as level": "ASLevel",
        "AS level": "ASLevel",
        "AS Level": "ASLevel",
        "aslevel": "ASLevel",
        "a_level": "ASLevel",
        "ASLevel": "ASLevel",
        
        "primary": "Primary School",
        "Primary": "Primary School",
        "primary school": "Primary School",
        "Primary School": "Primary School",
        "grade_7": "Primary School",
        "grade7": "Primary School",
        "Grade 7": "Primary School",
        "grade 7": "Primary School"
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
            
        # Initialize connection objects
        self.client = None
        self.db = None
        
        # Set instance variables from class constants
        self.db_name = self.DB_NAME  # Fix: Store DB_NAME as instance attribute
        self.uri = self.MONGODB_URI
        
        # Load credentials
        self._load_credentials()
        
        # Connection status
        self.connected = False
        
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
            
            # Report successful connection to NetworkMonitor
            from src.core.network.monitor import NetworkMonitor
            NetworkMonitor().report_mongodb_connection()
            
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
    
    def get_questions_by_subject_level(self, subject: str, level: str, limit: int = 30) -> List[Dict]:
        """
        Get questions for a specific subject and level
        
        Args:
            subject: Subject name
            level: Education level
            limit: Maximum number of questions to return
            
        Returns:
            List of question documents
        """
        logger.info(f"Getting questions for {subject} at {level} level (limit: {limit})")
        
        try:
            # Verify DB attributes are set correctly
            if not hasattr(self, 'db_name') or not self.db_name:
                logger.error("db_name attribute is not set properly")
                return []
                
            # Check subscription before accessing MongoDB
            if not self._check_subscription():
                logger.warning("Subscription not active, cannot fetch questions")
                return []
                
            # Ensure we're connected
            if not self._ensure_connected():
                logger.error("Failed to connect to MongoDB")
                return []
            
            # Get database references
            try:
                db = self.client[self.db_name]
                logger.debug(f"Successfully accessed database: {self.db_name}")
                
                # Check collections exist
                collections = db.list_collection_names()
                logger.debug(f"Available collections: {collections}")
                
                if "extracted-questions" not in collections:
                    logger.error(f"'extracted-questions' collection not found in database {self.db_name}")
                    return []
                
                if "extracted-answers" not in collections:
                    logger.warning(f"'extracted-answers' collection not found in database {self.db_name}")
                
                papers_collection = db["extracted-questions"]
                answers_collection = db["extracted-answers"]
            except Exception as e:
                logger.error(f"Error accessing collections: {e}")
                return []
            
            # Standardize subject and level names
            standardized_subject = self._standardize_subject_name(subject)
            standardized_level_q = self.QUESTION_LEVEL_MAPPING.get(level.lower(), level.lower())
            standardized_level_a = self.ANSWER_LEVEL_MAPPING.get(level.lower(), level)
            
            logger.info(f"Standardized subject: '{standardized_subject}', Question level: '{standardized_level_q}', Answer level: '{standardized_level_a}'")
            
            # Create query for questions
            query = {
                "paper_meta.Subject": {"$regex": standardized_subject, "$options": "i"},  # Case-insensitive subject match
                "paper_meta.Level": standardized_level_q  # Case-sensitive level match for questions
            }
            
            logger.info(f"Executing MongoDB query: {query}")
            
            # Find questions matching the query
            try:
                cursor = papers_collection.find(query).limit(limit)
                
                # Convert cursor to list and process each document
                question_docs = list(cursor)
                logger.info(f"Found {len(question_docs)} question documents")
                
                if len(question_docs) == 0:
                    # Try an alternate query with just the subject
                    alt_query = {"paper_meta.Subject": {"$regex": standardized_subject, "$options": "i"}}
                    logger.info(f"No questions found with original query. Trying alternate query: {alt_query}")
                    cursor = papers_collection.find(alt_query).limit(5)
                    sample_docs = list(cursor)
                    
                    if sample_docs:
                        # Log the actual levels in the database to help debug
                        levels = set()
                        for doc in sample_docs:
                            paper_meta = doc.get('paper_meta', {})
                            level_val = paper_meta.get('Level')
                            if level_val:
                                levels.add(level_val)
                        
                        logger.info(f"Found documents with subject '{standardized_subject}' and levels: {levels}")
                        logger.info(f"Expected level '{standardized_level_q}' not found. Make sure mapping is correct.")
                    else:
                        logger.warning(f"No documents found for subject '{standardized_subject}' at all")
            except Exception as e:
                logger.error(f"Error executing query: {e}")
                return []
            
            # Filter questions to only include those with matching answers
            filtered_questions = []
            for doc in question_docs:
                # Extract paper metadata for matching with answers
                paper_meta = doc.get('paper_meta', {})
                
                # Create query to find matching answer documents
                answer_query = {
                    "paper_meta.Subject": paper_meta.get("Subject"),
                    "paper_meta.Level": standardized_level_a,  # Use answer-specific level format
                    "paper_meta.Year": paper_meta.get("Year"),
                    "paper_meta.PaperNumber": paper_meta.get("PaperNumber"),
                    "paper_meta.Examining Board": paper_meta.get("Examining Board", paper_meta.get("ExaminingBoard"))
                }
                
                # Check if an answer document exists
                answer_exists = answers_collection.find_one(answer_query)
                
                if answer_exists:
                    # If matching answer exists, include this question
                    filtered_questions.append(doc)
                else:
                    logger.debug(f"Skipping question without matching answer: {paper_meta}")
            
            logger.info(f"Filtered to {len(filtered_questions)} questions with matching answers")
            
            # If no questions found with exact match, try a more flexible search
            if not filtered_questions:
                logger.info("No questions found with matching answers, trying more flexible search")
                
                # Try with just subject and level
                alt_query = {
                    "paper_meta.Subject": {"$regex": standardized_subject, "$options": "i"},
                    "paper_meta.Level": standardized_level_q
                }
                
                cursor = papers_collection.find(alt_query).limit(limit)
                question_docs = list(cursor)
                logger.info(f"Found {len(question_docs)} question documents with flexible search")
                
                # Still filter for matching answers
                for doc in question_docs:
                    paper_meta = doc.get('paper_meta', {})
                    answer_query = {
                        "paper_meta.Subject": paper_meta.get("Subject"),
                        "paper_meta.Level": standardized_level_a
                    }
                    
                    answer_exists = answers_collection.find_one(answer_query)
                    if answer_exists:
                        filtered_questions.append(doc)
                
                logger.info(f"Filtered to {len(filtered_questions)} questions with matching answers")
            
            return filtered_questions
            
        except Exception as e:
            logger.error(f"Error fetching questions: {str(e)}", exc_info=True)
            return []
            
    def _standardize_subject_name(self, subject: str) -> str:
        """Standardize subject name to match MongoDB schema"""
        # Remove spaces and convert to lowercase
        standardized = subject.lower().replace(" ", "")
        
        # Map common subject names
        subject_map = {
            "biology": "biology",
            "mathematics": "mathematics",
            "english": "englishlanguage",
            "physics": "physics",
            "chemistry": "chemistry",
            "history": "history",
            "geography": "geography",
            "business": "businessstudies",
            "accounting": "accounting",
            "economics": "economics",
            "computerscience": "computerscience"
        }
        
        return subject_map.get(standardized, standardized)
        
    def _standardize_level_name(self, level: str) -> str:
        """Standardize level name to match MongoDB schema"""
        # Remove spaces and convert to lowercase
        standardized = level.lower().replace(" ", "")
        
        # Map common level names
        level_map = {
            "grade7": "grade7",
            "olevel": "olevel",
            "alevel": "aslevel",  # Note 'a_level' maps to 'aslevel' in the database
            "a_level": "aslevel",
            "o_level": "olevel",
            "grade_7": "grade7",
            "primary": "grade7"
        }
        
        return level_map.get(standardized, standardized)
    
    def count_questions(self, subject: str, level: str) -> int:
        """
        Count the number of questions available for a given subject and level
        
        Args:
            subject: Subject name
            level: Education level
            
        Returns:
            Estimated count of questions
        """
        logger.info(f"Counting questions for {subject} at {level} level")
        
        try:
            # Check subscription
            if not self._check_subscription():
                logger.warning("Subscription not active, cannot count questions")
                return 0
                
            # Ensure connection
            if not self._ensure_connected():
                logger.error("Failed to connect to MongoDB")
                return 0
            
            # Get database references
            db = self.client[self.db_name]
            papers_collection = db["extracted-questions"]
            answers_collection = db["extracted-answers"]
            
            # Standardize subject and level names
            standardized_subject = self._standardize_subject_name(subject)
            standardized_level_q = self.QUESTION_LEVEL_MAPPING.get(level.lower(), level.lower())
            standardized_level_a = self.ANSWER_LEVEL_MAPPING.get(level.lower(), level)
            
            # Create query for questions
            query = {
                "paper_meta.Subject": {"$regex": standardized_subject, "$options": "i"},
                "paper_meta.Level": standardized_level_q
            }
            
            # Count papers matching the criteria
            paper_count = papers_collection.count_documents(query)
            
            # Check how many have matching answers
            papers_with_answers = 0
            cursor = papers_collection.find(query)
            
            for doc in cursor:
                paper_meta = doc.get('paper_meta', {})
                answer_query = {
                    "paper_meta.Subject": paper_meta.get("Subject"),
                    "paper_meta.Level": standardized_level_a,
                    "paper_meta.Year": paper_meta.get("Year"),
                    "paper_meta.PaperNumber": paper_meta.get("PaperNumber")
                }
                
                if answers_collection.find_one(answer_query):
                    papers_with_answers += 1
            
            logger.info(f"Found {paper_count} papers, {papers_with_answers} with matching answers")
            
            # Estimate number of questions (average 15 questions per paper)
            estimated_questions = papers_with_answers * 15
            return estimated_questions
            
        except Exception as e:
            logger.error(f"Error counting questions: {str(e)}")
            return 0
    
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
        Get the matching answer document for a question paper.
        PRIORITIZES matching by _id from the question_doc first.
        Falls back to metadata matching if _id match fails.

        Args:
            question_doc: The question document (potentially containing _id)

        Returns:
            The answer document, or None if no match is found
        """
        logger.info(f"--- Entered get_matching_answer (consolidated logic) ---")

        try:
            # --- Primary Match Attempt: Using _id ---
            question_object_id = None
            raw_id = question_doc.get('_id') # Get _id (could be string or ObjectId)

            if isinstance(raw_id, ObjectId):
                question_object_id = raw_id
            elif isinstance(raw_id, str):
                 try:
                      question_object_id = ObjectId(raw_id)
                      logger.debug(f"Converted question doc string ID '{raw_id}' to ObjectId: {question_object_id}")
                 except Exception:
                      logger.warning(f"Question doc _id '{raw_id}' is a string but not a valid ObjectId format. Cannot use for primary match.")
            else:
                logger.info(f"No usable '_id' field found in question_doc for primary matching.")


            if question_object_id: # Proceed only if we have a valid ObjectId
                 logger.info(f"Attempting primary match using _id: {question_object_id}")
                 if self._ensure_connected():
                     answers_collection = self.db["extracted-answers"]
                     answer_doc = answers_collection.find_one({'_id': question_object_id})
                     if answer_doc:
                         logger.info(f"Primary match SUCCESS using _id. Found answer doc: {answer_doc.get('_id')}")
                         return answer_doc # Return the successfully matched document
                     else:
                         logger.info(f"Primary match FAILED using _id {question_object_id} (returned None). Proceeding to metadata match.")
                 else:
                      logger.error("Cannot perform primary match by _id - MongoDB not connected.")
            # --- End Primary Match Attempt ---


            # --- Fallback Match Attempt: Using Metadata ---
            logger.info(f"Attempting fallback match using metadata...")
            if not self._ensure_connected():
                 logger.error("Cannot perform fallback match by metadata - MongoDB not connected.")
                 return None

            # Extract metadata needed for the fallback query
            paper_meta = question_doc.get('paper_meta', {})
            subject = paper_meta.get("Subject", question_doc.get("subject"))
            level = paper_meta.get("Level", question_doc.get("level"))
            year = paper_meta.get("Year", question_doc.get("year"))
            paper_number = paper_meta.get("PaperNumber")
            # Add Term and Version for more specificity if available
            term = paper_meta.get("Term", question_doc.get("Term"))
            version = paper_meta.get("Version", question_doc.get("Version"))


            if not subject or not level or not year: # Require at least these for a meaningful fallback
                 logger.warning(f"Insufficient metadata (subject/level/year missing) in question_doc for fallback matching. Doc _id: {question_doc.get('_id')}")
                 return None

            # Standardize for query
            standardized_subject = self._standardize_subject_name(subject) # Assuming this helper exists
            standardized_level_a = self.ANSWER_LEVEL_MAPPING.get(level.lower(), level) # Use ANSWER mapping

            # Build the metadata query - make it more specific
            query = {
                 "paper_meta.Subject": {"$regex": f"^{re.escape(standardized_subject)}$", "$options": "i"}, # Exact match, case-insensitive
                 "paper_meta.Level": standardized_level_a, # Use specific answer level format
                 "paper_meta.Year": str(year) # Ensure year is string
            }
            # Add other specific fields if available
            if paper_number: query["paper_meta.PaperNumber"] = str(paper_number)
            if term: query["paper_meta.Term"] = term
            if version: query["paper_meta.Version"] = str(version)
            # Add examining board if relevant and consistent
            # examining_board = paper_meta.get("Examining Board", paper_meta.get("ExaminingBoard"))
            # if examining_board: query["paper_meta.Examining Board"] = examining_board


            logger.info(f"Executing fallback metadata query: {query}")
            answers_collection = self.db["extracted-answers"]
            answer_doc = answers_collection.find_one(query) # Use find_one

            if answer_doc:
                 logger.info(f"Fallback match SUCCESS using metadata. Found answer doc: {answer_doc.get('_id')}")
                 return answer_doc
            else:
                 logger.warning(f"Fallback match FAILED using metadata. No matching answer document found.")
                 return None

        except SubscriptionRequiredError as e:
             logger.warning(f"Subscription error in get_matching_answer: {e}")
             return None
        except Exception as e:
            logger.error(f"Error in get_matching_answer: {e}", exc_info=True)
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
        """Check if user has an active subscription"""
        try:
            # Defer import to avoid circular dependency
            from src.core.network.sync_service import SyncService
            
            # Try Firebase client first for subscription status
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