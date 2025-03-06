import pymongo
import json
import sys
import os
import datetime
from bson.objectid import ObjectId

def connect_to_mongodb(mongodb_uri):
    """Connect to MongoDB and return database client"""
    client = pymongo.MongoClient(mongodb_uri)
    db = client["fundaAI"]
    return db

def update_document(db, doc_id, extraction_data):
    """
    Update MongoDB with extraction results
    
    Args:
        db: MongoDB database connection
        doc_id: Original document ID
        extraction_data: Extraction result data
        
    Returns:
        Result of the update operation
    """
    try:
        # Parse extraction data
        data = json.loads(extraction_data)
        
        if not data.get("success", False):
            # Update document with error status
            db["pp-questions"].update_one(
                {"_id": ObjectId(doc_id)},
                {
                    "$set": {
                        "Status": "error",
                        "Metadata.LastModified": datetime.datetime.now()
                    },
                    "$push": {
                        "ErrorLog": {
                            "timestamp": datetime.datetime.now(),
                            "message": data.get("error", "Unknown error during extraction")
                        }
                    }
                }
            )
            return {
                "success": False,
                "document_id": doc_id,
                "error": data.get("error", "Unknown error during extraction")
            }
        
        # Get document from MongoDB to access metadata
        original_doc = db["pp-questions"].find_one({"_id": ObjectId(doc_id)})
        
        if not original_doc:
            return {
                "success": False,
                "document_id": doc_id,
                "error": "Original document not found"
            }
        
        # Create document for extracted-questions collection
        extracted_doc = {
            "exam_id": data.get("file_id", original_doc["FileID"]),
            "paper_meta": {
                "Level": original_doc.get("Level", ""),
                "Subject": original_doc.get("Subject", ""),
                "Year": original_doc.get("Year", ""),
                "Paper": original_doc.get("Paper", ""),
                "Term": original_doc.get("Term", "")
            },
            "questions": data.get("extracted_questions", []),
            "total_questions": data.get("total_questions", 0),
            "extraction_date": datetime.datetime.now()
        }
        
        # Add Version if it exists
        if "Version" in original_doc:
            extracted_doc["paper_meta"]["Version"] = original_doc["Version"]
            
        # Insert into extracted-questions collection
        result = db["extracted-questions"].insert_one(extracted_doc)
        
        # Update original document
        db["pp-questions"].update_one(
            {"_id": ObjectId(doc_id)},
            {
                "$set": {
                    "Processed": True,
                    "ProcessedDate": datetime.datetime.now(),
                    "Status": "extracted",
                    "Metadata.TotalItems": data.get("total_questions", 0),
                    "Metadata.LastModified": datetime.datetime.now()
                }
            }
        )
        
        return {
            "success": True,
            "document_id": doc_id,
            "extracted_id": str(result.inserted_id),
            "question_count": data.get("total_questions", 0)
        }
        
    except Exception as e:
        import traceback
        
        # Update document with error status
        db["pp-questions"].update_one(
            {"_id": ObjectId(doc_id)},
            {
                "$set": {
                    "Status": "error",
                    "Metadata.LastModified": datetime.datetime.now()
                },
                "$push": {
                    "ErrorLog": {
                        "timestamp": datetime.datetime.now(),
                        "message": str(e)
                    }
                }
            }
        )
        
        return {
            "success": False,
            "document_id": doc_id,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

if __name__ == "__main__":
    # Get MongoDB URI from environment variable
    mongodb_uri = os.environ.get("MONGODB_URI")
    if not mongodb_uri:
        print(json.dumps({"error": "MONGODB_URI environment variable not set"}))
        sys.exit(1)
    
    # Get document ID and extraction data from arguments
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Missing required arguments: document_id extraction_data"}))
        sys.exit(1)
    
    doc_id = sys.argv[1]
    extraction_data = sys.argv[2]
    
    # Connect to MongoDB
    db = connect_to_mongodb(mongodb_uri)
    
    # Update document
    result = update_document(db, doc_id, extraction_data)
    
    # Return as JSON
    print(json.dumps(result))
