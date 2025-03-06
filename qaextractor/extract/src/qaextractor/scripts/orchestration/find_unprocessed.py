import pymongo
import json
import sys
import os

def connect_to_mongodb(mongodb_uri):
    """Connect to MongoDB and return database client"""
    client = pymongo.MongoClient(mongodb_uri)
    db = client["fundaAI"]
    return db

def find_unprocessed_documents(db, process_all=False, limit=10):
    """
    Find unprocessed documents in MongoDB
    
    Args:
        db: MongoDB database connection
        process_all: Whether to process all documents (ignore filter)
        limit: Maximum number of documents to return
        
    Returns:
        List of unprocessed documents
    """
    # Query for unprocessed documents
    query = {"Processed": {"$ne": True}}
    
    # If not processing all, add additional filters
    if not process_all:
        # You can add more specific filters here if needed
        pass
    
    # Find documents
    documents = list(db["pp-questions"].find(query).limit(limit))
    
    # Return document details
    result = []
    for doc in documents:
        doc_info = {
            "_id": str(doc["_id"]),
            "FileID": doc["FileID"],
            "FileName": doc.get("FileName", "Unknown"),
            "Level": doc.get("Level", ""),
            "Subject": doc.get("Subject", ""),
            "Year": doc.get("Year", ""),
            "Paper": doc.get("Paper", ""),
            "Term": doc.get("Term", ""),
        }
        
        # Add Version if it exists
        if "Version" in doc:
            doc_info["Version"] = doc["Version"]
            
        result.append(doc_info)
    
    return result

if __name__ == "__main__":
    # Get MongoDB URI from environment variable
    mongodb_uri = os.environ.get("MONGODB_URI")
    if not mongodb_uri:
        print(json.dumps({"error": "MONGODB_URI environment variable not set"}))
        sys.exit(1)
    
    # Process command line arguments
    process_all = len(sys.argv) > 1 and sys.argv[1] == "all"
    
    # Connect to MongoDB
    db = connect_to_mongodb(mongodb_uri)
    
    # Find unprocessed documents
    documents = find_unprocessed_documents(db, process_all)
    
    # Return as JSON
    print(json.dumps({"documents": documents}))
