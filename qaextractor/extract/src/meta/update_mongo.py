"""
Script to update MongoDB documents with extracted metadata.
"""

import json
import sys
import os
import pymongo
import datetime
from bson.objectid import ObjectId
from update import connect_to_mongodb, update_document_metadata

def update_with_metadata(doc_id, metadata_file):
    """Update MongoDB document with metadata from file"""
    try:
        # Load metadata
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Connect to MongoDB
        mongodb_uri = os.environ.get('MONGODB_URI')
        collection_name = os.environ.get('COLLECTION_NAME', 'extracted-questions')  # Get collection name
        
        if not mongodb_uri:
            return {
                "success": False,
                "document_id": doc_id,
                "error": "MONGODB_URI environment variable not set"
            }
            
        db = connect_to_mongodb(mongodb_uri)
        
        # Update document - pass collection_name parameter
        result = update_document_metadata(db, doc_id, metadata, collection_name)
        
        # Add metadata to result for logging
        result['metadata'] = metadata
        return result
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "document_id": doc_id,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({
            "success": False,
            "error": "Missing required arguments: doc_id metadata_file"
        }))
        sys.exit(1)
    
    doc_id = sys.argv[1]
    metadata_file = sys.argv[2]
    
    result = update_with_metadata(doc_id, metadata_file)
    print(json.dumps(result))
