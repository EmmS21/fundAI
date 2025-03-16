import pymongo
import json
import sys
import os

def connect_to_mongodb(mongodb_uri):
    """Connect to MongoDB and return database client"""
    client = pymongo.MongoClient(mongodb_uri)
    db = client["fundaAI"]
    return db

def find_unprocessed_documents(db, process_all=False, limit=10, skip=0):
    """
    Find unprocessed documents in MongoDB
    
    Args:
        db: MongoDB database connection
        process_all: Whether to process all documents (ignore filter)
        limit: Maximum number of documents to return
        skip: Number of documents to skip
        
    Returns:
        List of unprocessed documents
    """
    # Query for unprocessed documents
    query = {"Processed": {"$ne": True}}
    
    # If not processing all, add additional filters
    if not process_all:
        # You can add more specific filters here if needed
        pass
    
    # Find documents with skip, limit, and stable sorting by _id
    documents = list(db["pp-questions"]
                     .find(query)
                     .sort("_id", pymongo.ASCENDING)  # <-- Added stable sorting
                     .skip(skip)
                     .limit(limit))
    
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
    
    # Check for skip parameter
    skip = 0
    for i in range(1, len(sys.argv)):
        if sys.argv[i] == "--skip" and i + 1 < len(sys.argv):
            try:
                skip = int(sys.argv[i + 1])
            except ValueError:
                pass
    
    # Connect to MongoDB
    db = connect_to_mongodb(mongodb_uri)
    
    # Find unprocessed documents
    documents = find_unprocessed_documents(db, process_all, 10, skip)
    
    # Return as JSON
    print(json.dumps({"documents": documents}))
