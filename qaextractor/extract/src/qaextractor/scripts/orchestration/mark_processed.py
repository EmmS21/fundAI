import sys
import os
import json
import pymongo
import datetime
from bson.objectid import ObjectId

def mark_as_processed(doc_id, extraction_id=None, total_questions=0):
    """Mark a document as processed in the pp-questions collection"""
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient(os.environ.get("MONGODB_URI"))
        db = client["fundaAI"]
        
        # Check if document exists
        doc = db["pp-questions"].find_one({"_id": ObjectId(doc_id)})
        if not doc:
            return {"success": False, "error": f"Document {doc_id} not found"}
        
        # Prepare the update
        update_doc = {
            "Processed": True,
            "ProcessedDate": datetime.datetime.now(),
            "Status": "Extracted"
        }
        
        # Add metadata if available
        if extraction_id or total_questions > 0:
            metadata = {}
            if total_questions > 0:
                metadata["TotalQuestionsExtracted"] = total_questions
            if extraction_id:
                metadata["ExtractionId"] = extraction_id
                
            if metadata:
                update_doc["Metadata"] = metadata
        
        # Update the document
        result = db["pp-questions"].update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": update_doc}
        )
        
        return {
            "success": result.modified_count > 0,
            "document_id": doc_id,
            "matched_count": result.matched_count,
            "modified_count": result.modified_count
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Missing document ID"}))
        sys.exit(1)
    
    doc_id = sys.argv[1]
    
    # Optional parameters
    extraction_id = None
    total_questions = 0
    
    # Check for extraction_id as third argument
    if len(sys.argv) > 2:
        extraction_id = sys.argv[2]
    
    # Check for total_questions as fourth argument
    if len(sys.argv) > 3:
        try:
            total_questions = int(sys.argv[3])
        except ValueError:
            pass
    
    result = mark_as_processed(doc_id, extraction_id, total_questions)
    print(json.dumps(result))
