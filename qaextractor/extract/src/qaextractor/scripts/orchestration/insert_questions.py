import json
import sys
import os
import pymongo
import datetime
import traceback

def insert_questions(doc_id, extraction_data_str):
    # Check if the input is a file path
    if os.path.exists(extraction_data_str):
        try:
            with open(extraction_data_str, 'r') as f:
                extraction_data = f.read()
        except Exception as e:
            print(json.dumps({
                "success": False,
                "error": f"Error reading file: {str(e)}"
            }))
            return
    else:
        extraction_data = extraction_data_str
    
    # Parse the JSON data
    try:
        data = json.loads(extraction_data)
    except json.JSONDecodeError as e:
        print(json.dumps({
            "success": False,
            "error": f"Invalid JSON: {str(e)}"
        }))
        return
    
    # Connect to MongoDB
    try:
        # Get MongoDB connection string from environment variable
        mongodb_uri = os.environ.get("MONGODB_URI")
        if not mongodb_uri:
            print(json.dumps({
                "success": False,
                "error": "MONGODB_URI environment variable not set"
            }))
            return
        
        client = pymongo.MongoClient(mongodb_uri)
        client.admin.command('ping')  # Test connection
        db = client.fundaAI
        
        # Extract the questions from the data
        extracted_questions = data.get("extracted_questions", [])
        
        # Insert the extraction document
        extraction_doc = {
            "document_id": doc_id,
            "extraction_date": datetime.datetime.now(),
            "file_id": data.get("file_id", ""),
            "file_name": data.get("file_name", ""),
            "collection_name": data.get("collection_name", ""),
            "questions": extracted_questions,
            "total_questions": len(extracted_questions)
        }
        
        result = db["extracted-questions"].insert_one(extraction_doc)
        extraction_id = str(result.inserted_id)
        
        # Return success result
        result = {
            "success": True,
            "extraction_id": extraction_id,
            "total_questions": len(extracted_questions)
        }
        print(json.dumps(result))
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"MongoDB error: {str(e)}"
        }))

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Insert extracted questions into MongoDB")
    parser.add_argument("doc_id", help="MongoDB document ID")
    parser.add_argument("extraction_data", help="Extraction data JSON or file path")
    parser.add_argument("--file", action="store_true", help="Treat extraction_data as a file path")
    
    args = parser.parse_args()
    
    # Get doc_id
    doc_id = args.doc_id
    
    # If the --file flag is provided, treat the extraction_data as a file path
    if args.file:
        # Make sure we properly handle file paths
        if os.path.exists(args.extraction_data):
            with open(args.extraction_data, 'r') as f:
                extraction_data = f.read()
        else:
            print(json.dumps({
                "success": False,
                "error": f"File not found: {args.extraction_data}"
            }))
            sys.exit(1)  # Exit with error code
    else:
        # Use the extraction_data argument directly as a JSON string
        extraction_data = args.extraction_data
    
    # Call the main function
    try:
        insert_questions(doc_id, extraction_data)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Uncaught exception: {str(e)}"
        }))
        sys.exit(1)
