"""
Module for updating paper metadata in MongoDB records.
This script finds and updates extracted-questions entries that are missing paper_meta information.
"""

import json
import sys
import os
import pymongo
import datetime
import re
from bson.objectid import ObjectId

def connect_to_mongodb(mongodb_uri):
    """Connect to MongoDB and return database client"""
    client = pymongo.MongoClient(mongodb_uri)
    db = client["fundaAI"]
    return db

def find_documents_missing_metadata(db, collection_name, limit=10, skip=0):
    """
    Find documents in the specified collection that have missing or incomplete paper_meta
    """
    # Query for documents missing paper_meta or with incomplete paper_meta
    query = {
        "$or": [
            {"paper_meta": {"$exists": False}},
            {"paper_meta.Level": {"$in": ["", None]}},
            {"paper_meta.Subject": {"$in": ["", None]}},
            {"paper_meta.Year": {"$in": ["", None]}},
            {"paper_meta.Paper": {"$in": ["", None]}}
        ]
    }
    
    # Find documents with skip, limit, and stable sorting by _id
    documents = list(db[collection_name]
                    .find(query)
                    .sort("_id", pymongo.ASCENDING)
                    .skip(skip)
                    .limit(limit))
    
    # Convert ObjectId to string for JSON serialization
    for doc in documents:
        doc["_id"] = str(doc["_id"])
    
    return documents

def extract_metadata_from_filename(filename):
    """Extract metadata from filename based on patterns"""
    metadata = {
        "Paper": "",
        "Version": ""
    }
    
    # Check for Paper-{number}:{version}.pdf pattern
    paper_pattern = r'Paper-(\d+)(?::(\d+))?\.pdf'
    match = re.search(paper_pattern, filename)
    if match:
        metadata["Paper"] = match.group(1)
        if match.group(2):
            metadata["Version"] = match.group(2)
    
    return metadata

def update_document_metadata(db, doc_id, paper_meta, collection_name):
    """Update paper_meta in the specified collection"""
    try:
        result = db[collection_name].update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {
                "paper_meta": paper_meta,
                "updated_at": datetime.datetime.now()
            }}
        )
        
        return {
            "success": result.modified_count > 0,
            "document_id": doc_id,
            "matched_count": result.matched_count,
            "modified_count": result.modified_count
        }
    except Exception as e:
        return {"success": False, "document_id": doc_id, "error": str(e)}

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

def main():
    """Main function for running outside of Dagger"""
    mongodb_uri = os.environ.get("MONGODB_URI")
    collection_name = os.environ.get("COLLECTION_NAME", "extracted-questions")  # Default to questions
    if not mongodb_uri:
        print(json.dumps({"success": False, "error": "MONGODB_URI environment variable not set"}))
        sys.exit(1)
    
    limit = int(os.environ.get("BATCH_SIZE", "10"))
    skip = int(os.environ.get("SKIP", "0"))
    
    db = connect_to_mongodb(mongodb_uri)
    documents = find_documents_missing_metadata(db, collection_name, limit, skip)
    
    serializable_documents = json_serialize_mongodb(documents)
    print(json.dumps({"success": True, "documents": serializable_documents}))

if __name__ == "__main__":
    main()
