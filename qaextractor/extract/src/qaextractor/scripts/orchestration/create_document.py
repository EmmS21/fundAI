import json
import datetime
import sys
import os
import pymongo

def create_document(level_name, subject_name, year, paper_info, folder_path, doc_type, mongodb_uri):
    """
    Create a MongoDB document for a paper and insert it into the database
    
    Args:
        level_name (str): Education level (ASLevel, OLevel, Primary)
        subject_name (str): Subject name
        year (str): Year of the paper
        paper_info (dict): Paper information including paper number, term, version, etc.
        folder_path (list): Path to the file in Google Drive
        doc_type (str): Document type ("questions" or "answers")
        mongodb_uri (str): MongoDB connection string
    
    Returns:
        dict: Result of the operation including success status and document ID
    """
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient(mongodb_uri)
        db = client["fundaAI"]
        
        # Select the appropriate collection based on document type
        collection_name = "pp-questions" if doc_type == "questions" else "pp-answers"
        collection = db[collection_name]
        
        # Current timestamp
        now = datetime.datetime.utcnow()
        
        # Create document
        document = {
            "Level": level_name,
            "Subject": subject_name,
            "Year": year,
            "Paper": paper_info["paper"],
            "Term": paper_info["term"],
            "FileName": paper_info.get("name", ""),
            "FileID": paper_info["id"],
            "Processed": False,
            "ProcessedDate": None,
            "FolderStructure": folder_path,
            "DocumentType": doc_type,
            "Content": [],  # Will be populated during processing
            "Metadata": {
                "TotalPages": 0,
                "TotalItems": 0,
                "ExtractionDate": now,
                "LastModified": now
            },
            "Status": "pending",
            "ErrorLog": []
        }
        
        # Add version if present
        if paper_info.get("version") is not None:
            document["Version"] = paper_info["version"]
        
        # Insert or update document
        result = collection.update_one(
            {"FileID": paper_info["id"]},
            {"$set": document},
            upsert=True
        )
        
        # Return result
        if result.upserted_id:
            return {
                "success": True,
                "action": "inserted",
                "document_id": str(result.upserted_id),
                "collection": collection_name
            }
        elif result.modified_count > 0:
            return {
                "success": True,
                "action": "updated",
                "modified_count": result.modified_count,
                "collection": collection_name
            }
        else:
            return {
                "success": True,
                "action": "no_change",
                "collection": collection_name
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    # Get arguments from command line or stdin
    if len(sys.argv) > 1:
        # Command line arguments
        if len(sys.argv) < 6:
            print(json.dumps({
                "success": False,
                "error": "Missing required arguments"
            }))
            sys.exit(1)
            
        level_name = sys.argv[1]
        subject_name = sys.argv[2]
        year = sys.argv[3]
        paper_info_json = sys.argv[4]
        folder_path_json = sys.argv[5]
        doc_type = sys.argv[6]
        mongodb_uri = sys.argv[7] if len(sys.argv) > 7 else os.environ.get("MONGODB_URI")
        
        try:
            paper_info = json.loads(paper_info_json)
            folder_path = json.loads(folder_path_json)
        except json.JSONDecodeError as e:
            print(json.dumps({
                "success": False,
                "error": f"Invalid JSON: {str(e)}"
            }))
            sys.exit(1)
    else:
        # Read from stdin
        try:
            input_data = json.loads(sys.stdin.read())
            level_name = input_data.get("level_name")
            subject_name = input_data.get("subject_name")
            year = input_data.get("year")
            paper_info = input_data.get("paper_info")
            folder_path = input_data.get("folder_path")
            doc_type = input_data.get("doc_type")
            mongodb_uri = input_data.get("mongodb_uri") or os.environ.get("MONGODB_URI")
            
            if not all([level_name, subject_name, year, paper_info, folder_path, doc_type, mongodb_uri]):
                print(json.dumps({
                    "success": False,
                    "error": "Missing required fields in input"
                }))
                sys.exit(1)
        except json.JSONDecodeError as e:
            print(json.dumps({
                "success": False,
                "error": f"Invalid JSON input: {str(e)}"
            }))
            sys.exit(1)
    
    # Create document
    result = create_document(level_name, subject_name, year, paper_info, folder_path, doc_type, mongodb_uri)
    
    # Output result
    print(json.dumps(result)) 