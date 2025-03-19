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

# Import our credential manager
from .credential_manager import CredentialManager

# Set up logging
logger = logging.getLogger(__name__)

class MongoDBClient:
    """
    Client for connecting to MongoDB and retrieving exam questions.
    Implements connection pooling, retry logic, and standardization of fields.
    """
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one instance exists"""
        if cls._instance is None:
            cls._instance = super(MongoDBClient, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
        
    def __init__(self):
        """Initialize the MongoDB client with connection parameters"""
        if self.initialized:
            return
            
        self.client = None
        self.db = None
        self.connected = False
        
        # Default connection timeout (5 seconds)
        self.timeout_ms = 5000
        
        # Subject standardization mapping
        self.subject_mapping = {
            'ACCOUNTING': 'Accounting',
            'ADDITIONAL MATHEMATICS': 'Additional Mathematics',
            'BIOLOGY': 'Biology',
            'COMPUTER SCIENCE': 'Computer Science',
            'ECONOMICS': 'Economics',
            'ENGLISH LANGUAGE': 'English Language',
            'ENGLISHLANGUAGE': 'English Language',
            'HISTORY': 'History',
            'Mathematics': 'Mathematics',
            'Physics': 'Physics',
            'Science': 'Science'
        }
        
        # Level standardization mapping
        self.level_mapping = {
            'aslevel': 'a_level',
            'olevel': 'o_level',
            'primary school': 'grade_7'
        }
        
        # Term standardization mapping to summer/winter
        self.term_mapping = {
            'July': 'summer',
            'August': 'summer',
            'September': 'summer',
            'October': 'summer',
            'October/November': 'summer',
            'Nov/Dec': 'summer',
            'November': 'summer',
            'December': 'summer',
            'January': 'winter',
            'February': 'winter',
            'February/March': 'winter',
            'March': 'winter',
            'April': 'winter',
            'May': 'winter',
            'May/June': 'winter',
            'June': 'winter'
        }
        
        # Create credential manager
        self.credential_manager = CredentialManager()
        
        # Load credentials
        self._load_credentials()
        self.initialized = True
    
    def _load_credentials(self):
        """
        Load MongoDB connection credentials from secure storage.
        """
        # Get credentials from secure storage
        self.connection_uri, self.db_name = self.credential_manager.get_credentials()
        
        # If no credentials found, log a warning
        if not self.connection_uri:
            logger.warning("MongoDB credentials not found in secure storage. Please configure credentials.")
    
    def setup_credentials(self, uri: str, db_name: str) -> bool:
        """
        Set up MongoDB credentials and store them securely.
        
        Args:
            uri: MongoDB connection URI
            db_name: Database name to use
            
        Returns:
            bool: True if credentials were stored successfully
        """
        # Validate connection before storing
        try:
            # Test connection with provided credentials
            test_client = MongoClient(
                uri,
                serverSelectionTimeoutMS=5000
            )
            test_client.admin.command('ping')
            test_db = test_client[db_name]
            
            # Check if we can access the questions collection
            test_db.questions.find_one({})
            
            # Close test connection
            test_client.close()
            
            # Store credentials securely
            if self.credential_manager.store_credentials(uri, db_name):
                # Update current instance
                self.connection_uri = uri
                self.db_name = db_name
                
                # Reconnect with new credentials
                if self.connected:
                    self.disconnect()
                    
                return self.connect()
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to validate MongoDB credentials: {e}")
            return False
    
    def has_credentials(self) -> bool:
        """Check if we have stored credentials"""
        return self.credential_manager.has_credentials()
    
    @backoff.on_exception(backoff.expo, 
                         (ConnectionFailure, ServerSelectionTimeoutError),
                         max_tries=5)
    def connect(self) -> bool:
        """
        Establish connection to MongoDB with retry logic.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if self.connected and self.client:
            return True
            
        try:
            # Check if we have credentials
            if not self.connection_uri:
                logger.error("Cannot connect to MongoDB: No connection URI provided")
                return False
                
            # Connect with timeout
            self.client = MongoClient(
                self.connection_uri,
                serverSelectionTimeoutMS=self.timeout_ms
            )
            
            # Test connection
            self.client.admin.command('ping')
            
            # Access the database
            self.db = self.client[self.db_name]
            
            logger.info(f"Successfully connected to MongoDB database: {self.db_name}")
            self.connected = True
            return True
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Close the MongoDB connection"""
        if self.client:
            self.client.close()
            self.connected = False
            self.client = None
            logger.info("Disconnected from MongoDB")
    
    def _ensure_connected(self) -> bool:
        """Ensure we have an active connection to MongoDB"""
        if not self.connected:
            return self.connect()
        return True
    
    def _standardize_subject(self, subject: str) -> str:
        """Convert subject to standard format"""
        # Check direct mapping
        if subject in self.subject_mapping:
            return self.subject_mapping[subject]
        
        # Try case-insensitive match
        for key, value in self.subject_mapping.items():
            if subject.lower() == key.lower():
                return value
        
        # Return original if no mapping found
        return subject
    
    def _standardize_level(self, level: str) -> str:
        """Convert level to standard format"""
        if level in self.level_mapping:
            return self.level_mapping[level]
        return level
    
    def _standardize_term(self, term: str) -> str:
        """Convert term to summer/winter format"""
        for month, season in self.term_mapping.items():
            if month in term:
                return season
        
        # Default to summer if unknown
        return "summer"
    
    def get_questions_by_subject_level(self, subject: str, level: str, 
                                       limit: int = 50, year: Optional[str] = None) -> List[Dict]:
        """
        Get questions for a specific subject and level.
        
        Args:
            subject: The subject name (will be standardized)
            level: The level (will be standardized)
            limit: Maximum number of questions to return
            year: Optional specific year to filter by
            
        Returns:
            List of question documents
        """
        if not self._ensure_connected():
            logger.error("Cannot retrieve questions: Not connected to MongoDB")
            return []
        
        # Standardize inputs
        std_subject = self._standardize_subject(subject)
        std_level = self._standardize_level(level)
        
        # Build query
        query = {
            "$or": [
                {"paper_meta.Subject": {"$regex": f"^{std_subject}$", "$options": "i"}},
                {"paper_meta.StandardizedSubject": {"$regex": f"^{std_subject.lower().replace(' ', '')}$", "$options": "i"}}
            ],
            "paper_meta.Level": {"$regex": f"^{level}$", "$options": "i"}
        }
        
        # Add year filter if provided
        if year:
            query["paper_meta.Year"] = year
            
        try:
            # Execute query
            cursor = self.db.questions.find(query).limit(limit)
            
            # Process results
            questions = []
            for doc in cursor:
                # Process the document
                self._process_document_id(doc)
                questions.append(doc)
                
            logger.info(f"Retrieved {len(questions)} questions for {std_subject} at {std_level} level")
            return questions
            
        except Exception as e:
            logger.error(f"Error retrieving questions: {e}")
            return []
    
    def get_questions_by_topic(self, subject: str, topic: str, limit: int = 50) -> List[Dict]:
        """
        Get questions for a specific topic within a subject.
        
        Args:
            subject: The subject name (will be standardized)
            topic: The topic to search for
            limit: Maximum number of questions to return
            
        Returns:
            List of question documents
        """
        if not self._ensure_connected():
            logger.error("Cannot retrieve questions: Not connected to MongoDB")
            return []
        
        # Standardize subject
        std_subject = self._standardize_subject(subject)
        
        # Build query
        query = {
            "$or": [
                {"paper_meta.Subject": {"$regex": f"^{std_subject}$", "$options": "i"}},
                {"paper_meta.StandardizedSubject": {"$regex": f"^{std_subject.lower().replace(' ', '')}$", "$options": "i"}}
            ],
            "questions.topic": {"$regex": topic, "$options": "i"}
        }
            
        try:
            # Execute query
            cursor = self.db.questions.find(query).limit(limit)
            
            # Process results
            questions = []
            for doc in cursor:
                # Process the document
                self._process_document_id(doc)
                questions.append(doc)
                
            logger.info(f"Retrieved {len(questions)} questions for topic '{topic}' in {std_subject}")
            return questions
            
        except Exception as e:
            logger.error(f"Error retrieving questions by topic: {e}")
            return []
    
    def get_available_subjects(self) -> List[str]:
        """
        Get a list of all available subjects in the database.
        
        Returns:
            List of standardized subject names
        """
        if not self._ensure_connected():
            logger.error("Cannot retrieve subjects: Not connected to MongoDB")
            return []
        
        try:
            # Get distinct subject values
            raw_subjects = self.db.questions.distinct("paper_meta.Subject")
            
            # Standardize subject names
            standardized_subjects = set()
            for subject in raw_subjects:
                if subject:  # Skip None or empty strings
                    std_subject = self._standardize_subject(subject)
                    standardized_subjects.add(std_subject)
            
            return sorted(list(standardized_subjects))
            
        except Exception as e:
            logger.error(f"Error retrieving available subjects: {e}")
            return []
    
    def get_available_levels(self) -> List[str]:
        """
        Get a list of all available levels in the database.
        
        Returns:
            List of standardized level names
        """
        if not self._ensure_connected():
            logger.error("Cannot retrieve levels: Not connected to MongoDB")
            return []
        
        try:
            # Get distinct level values
            raw_levels = self.db.questions.distinct("paper_meta.Level")
            
            # Standardize level names
            standardized_levels = set()
            for level in raw_levels:
                if level:  # Skip None or empty strings
                    std_level = self._standardize_level(level)
                    standardized_levels.add(std_level)
            
            return sorted(list(standardized_levels))
            
        except Exception as e:
            logger.error(f"Error retrieving available levels: {e}")
            return []
    
    def get_available_years(self, subject: Optional[str] = None, level: Optional[str] = None) -> List[str]:
        """
        Get a list of all available years in the database, optionally filtered by subject and level.
        
        Args:
            subject: Optional subject filter
            level: Optional level filter
            
        Returns:
            List of years as strings
        """
        if not self._ensure_connected():
            logger.error("Cannot retrieve years: Not connected to MongoDB")
            return []
        
        try:
            # Build query for filtering
            query = {}
            
            if subject:
                std_subject = self._standardize_subject(subject)
                query["$or"] = [
                    {"paper_meta.Subject": {"$regex": f"^{std_subject}$", "$options": "i"}},
                    {"paper_meta.StandardizedSubject": {"$regex": f"^{std_subject.lower().replace(' ', '')}$", "$options": "i"}}
                ]
            
            if level:
                std_level = self._standardize_level(level)
                query["paper_meta.Level"] = {"$regex": f"^{level}$", "$options": "i"}
            
            # Get distinct year values
            years = self.db.questions.distinct("paper_meta.Year", query)
            
            # Remove empty values and sort
            valid_years = [year for year in years if year]
            return sorted(valid_years, reverse=True)  # Most recent first
            
        except Exception as e:
            logger.error(f"Error retrieving available years: {e}")
            return []
    
    def get_question_by_id(self, question_id: str) -> Optional[Dict]:
        """
        Get a specific question by its MongoDB ID.
        
        Args:
            question_id: The MongoDB ObjectId as a string
            
        Returns:
            Question document or None if not found
        """
        if not self._ensure_connected():
            logger.error("Cannot retrieve question: Not connected to MongoDB")
            return None
        
        try:
            # Convert string ID to ObjectId
            from bson.objectid import ObjectId
            obj_id = ObjectId(question_id)
            
            # Query by ID
            doc = self.db.questions.find_one({"_id": obj_id})
            
            if doc:
                # Process the document ID
                self._process_document_id(doc)
                return doc
            else:
                logger.warning(f"No question found with ID: {question_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving question by ID: {e}")
            return None
    
    def _process_document_id(self, doc: Dict):
        """
        Process MongoDB document to convert ObjectId to string.
        Modifies the document in-place.
        """
        if "_id" in doc and hasattr(doc["_id"], "__str__"):
            doc["_id"] = str(doc["_id"])
        return doc
    
    def get_random_questions(self, subject: str, level: str, count: int = 10) -> List[Dict]:
        """
        Get random questions for a specific subject and level.
        
        Args:
            subject: The subject name
            level: The level
            count: Number of questions to return
            
        Returns:
            List of question documents
        """
        if not self._ensure_connected():
            logger.error("Cannot retrieve random questions: Not connected to MongoDB")
            return []
        
        # Standardize inputs
        std_subject = self._standardize_subject(subject)
        std_level = self._standardize_level(level)
        
        try:
            # Build query
            query = {
                "$or": [
                    {"paper_meta.Subject": {"$regex": f"^{std_subject}$", "$options": "i"}},
                    {"paper_meta.StandardizedSubject": {"$regex": f"^{std_subject.lower().replace(' ', '')}$", "$options": "i"}}
                ],
                "paper_meta.Level": {"$regex": f"^{level}$", "$options": "i"}
            }
            
            # Use aggregation pipeline with $sample to get random documents
            pipeline = [
                {"$match": query},
                {"$sample": {"size": count}}
            ]
            
            cursor = self.db.questions.aggregate(pipeline)
            
            # Process results
            questions = []
            for doc in cursor:
                # Process the document
                self._process_document_id(doc)
                questions.append(doc)
                
            logger.info(f"Retrieved {len(questions)} random questions for {std_subject} at {std_level} level")
            return questions
            
        except Exception as e:
            logger.error(f"Error retrieving random questions: {e}")
            return []
    
    def get_questions_count(self, subject: Optional[str] = None, level: Optional[str] = None) -> int:
        """
        Get the count of questions matching the given filters.
        
        Args:
            subject: Optional subject filter
            level: Optional level filter
            
        Returns:
            Count of matching questions
        """
        if not self._ensure_connected():
            logger.error("Cannot count questions: Not connected to MongoDB")
            return 0
        
        try:
            # Build query
            query = {}
            
            if subject:
                std_subject = self._standardize_subject(subject)
                query["$or"] = [
                    {"paper_meta.Subject": {"$regex": f"^{std_subject}$", "$options": "i"}},
                    {"paper_meta.StandardizedSubject": {"$regex": f"^{std_subject.lower().replace(' ', '')}$", "$options": "i"}}
                ]
            
            if level:
                std_level = self._standardize_level(level)
                query["paper_meta.Level"] = {"$regex": f"^{level}$", "$options": "i"}
            
            # Count documents
            count = self.db.questions.count_documents(query)
            
            return count
            
        except Exception as e:
            logger.error(f"Error counting questions: {e}")
            return 0

    def get_topics_for_subject(self, subject: str) -> List[str]:
        """
        Get a list of all topics available for a given subject.
        
        Args:
            subject: The subject name
            
        Returns:
            List of topic names
        """
        if not self._ensure_connected():
            logger.error("Cannot retrieve topics: Not connected to MongoDB")
            return []
        
        # Standardize subject
        std_subject = self._standardize_subject(subject)
        
        try:
            # Build query
            query = {
                "$or": [
                    {"paper_meta.Subject": {"$regex": f"^{std_subject}$", "$options": "i"}},
                    {"paper_meta.StandardizedSubject": {"$regex": f"^{std_subject.lower().replace(' ', '')}$", "$options": "i"}}
                ]
            }
            
            # Use distinct to get unique topics
            # This assumes topics are stored directly in questions array
            pipeline = [
                {"$match": query},
                {"$unwind": "$questions"},
                {"$group": {"_id": "$questions.topic"}}
            ]
            
            cursor = self.db.questions.aggregate(pipeline)
            
            # Extract topics
            topics = []
            for doc in cursor:
                if doc["_id"] and doc["_id"] not in topics:
                    topics.append(doc["_id"])
            
            return sorted(topics)
            
        except Exception as e:
            logger.error(f"Error retrieving topics for subject: {e}")
            return [] 