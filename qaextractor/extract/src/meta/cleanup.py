"""
Module for cleaning up the MongoDB database.
This script handles removing duplicates and empty entries from the extracted-questions collection.
"""

import json
import sys
import os
import pymongo
import datetime
from bson.objectid import ObjectId

def json_serialize_mongodb(obj):
    """Convert MongoDB objects to JSON-serializable format"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: json_serialize_mongodb(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [json_serialize_mongodb(item) for item in obj]
    return obj

def connect_to_mongodb(mongodb_uri):
    """Connect to MongoDB and return database client"""
    client = pymongo.MongoClient(mongodb_uri)
    db = client["fundaAI"]
    return db

def cleanup_database(mongodb_uri):
    """
    Clean up database by removing duplicates and empty entries
    
    Args:
        mongodb_uri: MongoDB connection string
    
    Returns:
        dict: Statistics about the cleanup operation
    """
    client = pymongo.MongoClient(mongodb_uri)
    db = client["fundaAI"]
    
    # Statistics
    duplicates_removed = 0
    empty_entries_removed = 0
    
    # Find and remove empty entries (documents with no questions)
    empty_result = db["extracted-questions"].delete_many({
        "$or": [
            {"questions": {"$exists": False}},
            {"questions": []},
            {"total_questions": 0}
        ]
    })
    empty_entries_removed = empty_result.deleted_count
    
    # Find duplicates (based on exam_id)
    # First, find all unique exam_ids
    all_exam_ids = db["extracted-questions"].distinct("exam_id")
    
    # For each exam_id, keep only the most recent document
    for exam_id in all_exam_ids:
        if not exam_id:  # Skip if exam_id is None or empty
            continue
            
        # Find all documents with this exam_id
        documents = list(db["extracted-questions"].find({"exam_id": exam_id}).sort("extraction_date", -1))
        
        # If there's more than one document, delete all but the first (most recent)
        if len(documents) > 1:
            # Keep the first document (most recent by sort order)
            keep_id = documents[0]["_id"]
            
            # Delete all others
            delete_result = db["extracted-questions"].delete_many({
                "exam_id": exam_id,
                "_id": {"$ne": keep_id}
            })
            
            duplicates_removed += delete_result.deleted_count
    
    return {
        "success": True,
        "duplicates_removed": duplicates_removed,
        "empty_entries_removed": empty_entries_removed
    }

def main():
    """Main function for running as a standalone script"""
    mongodb_uri = os.environ.get("MONGODB_URI")
    if not mongodb_uri:
        print(json.dumps({"success": False, "error": "MONGODB_URI environment variable not set"}))
        sys.exit(1)
    
    result = cleanup_database(mongodb_uri)
    print(json.dumps(json_serialize_mongodb(result)))

if __name__ == "__main__":
    main()
