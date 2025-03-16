import sys
import json
import pymongo
import datetime
import os
from bson.objectid import ObjectId

def update_document(db, doc_id, extraction_data):
    """Update MongoDB with extraction results"""
    try:
        # Parse the extraction data
        try:
            data = json.loads(extraction_data)
        except Exception as e:
            print(f"ERROR: Failed to parse extraction data: {str(e)}")
            return {"success": False, "document_id": doc_id, "error": f"Invalid extraction data: {str(e)}"}
            
        # Get the original document
        original_doc = db["pp-questions"].find_one({"_id": ObjectId(doc_id)})
        if not original_doc:
            print(f"ERROR: Document not found: {doc_id}")
            return {"success": False, "document_id": doc_id, "error": "Document not found"}
        
        # Debug output
        print(f"DEBUG: Processing document {doc_id}, extraction data has {len(data.get('extracted_questions', []))} questions")
        
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
        
        print(f"DEBUG: Inserting document to extracted-questions collection")
            
        # Insert into extracted-questions collection
        try:
            result = db["extracted-questions"].insert_one(extracted_doc)
            print(f"DEBUG: Successfully inserted document with ID: {result.inserted_id}")
        except Exception as e:
            print(f"ERROR: Failed to insert into extracted-questions: {str(e)}")
            return {"success": False, "document_id": doc_id, "error": f"Insert error: {str(e)}"}
        
        print(f"DEBUG: Preparing to update original document: {doc_id}")
        
        # Update original document
        try:
            update_dict = {
                "$set": {
                    "Processed": True,
                    "ProcessedDate": datetime.datetime.now(),
                    "Status": "extracted",
                    "Metadata.TotalItems": data.get("total_questions", 0),
                    "Metadata.LastModified": datetime.datetime.now()
                }
            }
            print(f"DEBUG: Update operation: {json.dumps(update_dict, default=str)}")
            
            update_result = db["pp-questions"].update_one(
                {"_id": ObjectId(doc_id)},
                update_dict
            )
            
            print(f"DEBUG: Update result - Modified count: {update_result.modified_count}, Matched count: {update_result.matched_count}")
            
            if update_result.matched_count == 0:
                print(f"ERROR: No documents matched the ID {doc_id} during update")
                return {"success": False, "document_id": doc_id, "error": "No matching document during update"}
            elif update_result.modified_count == 0:
                print(f"WARNING: Document matched but not modified. Document may already be processed.")
            
            return {
                "success": True,
                "document_id": doc_id,
                "extracted_id": str(result.inserted_id),
                "question_count": data.get("total_questions", 0),
                "modified_count": update_result.modified_count,
                "matched_count": update_result.matched_count
            }
        except Exception as e:
            print(f"ERROR: Failed to update pp-questions: {str(e)}")
            return {"success": False, "document_id": doc_id, "error": f"Update error: {str(e)}"}
            
    except Exception as e:
        print(f"ERROR: Exception in update_document: {str(e)}")
        return {"success": False, "document_id": doc_id, "error": str(e)}

if __name__ == "__main__":
    # Check arguments
    if len(sys.argv) < 3:
        print(json.dumps({"success": False, "error": "Missing required arguments"}))
        sys.exit(1)
    
    doc_id = sys.argv[1]
    
    # Check if we should read from a file
    if "--file" in sys.argv:
        # The second argument is the file path
        file_path = sys.argv[2]
        try:
            print(f"DEBUG: Reading extraction data from file: {file_path}")
            with open(file_path, 'r') as f:
                extraction_data = f.read()
            print(f"DEBUG: Successfully read {len(extraction_data)} characters from file")
        except Exception as e:
            print(json.dumps({"success": False, "error": f"Failed to read file: {str(e)}"}))
            sys.exit(1)
    else:
        # Use the command line argument directly
        extraction_data = sys.argv[2]
    
    # Connect to MongoDB
    try:
        client = pymongo.MongoClient(os.environ.get("MONGODB_URI"))
        db = client["fundaAI"]
        
        # Update document and get result
        result = update_document(db, doc_id, extraction_data)
        
        # Return JSON result
        print(json.dumps(result))
        
    except Exception as e:
        print(json.dumps({"success": False, "document_id": doc_id, "error": str(e)}))
