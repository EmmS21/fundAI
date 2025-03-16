import json
import sys
import os
import pymongo
import datetime

def insert_answers(doc_id, extraction_data_str, matching_question_id=None):
    """
    Insert extracted answers into MongoDB
    
    Args:
        doc_id: MongoDB document ID of the original answer document
        extraction_data_str: Extracted answer data as JSON string or file path
        matching_question_id: ID of the matching question document
        
    Returns:
        JSON result with success status and extracted ID
    """
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
        
        # Extract the answers from the data
        extracted_answers = data.get("extracted_answers", [])
        
        # Insert the extraction document
        extraction_doc = {
            "document_id": doc_id,
            "matching_question_id": matching_question_id,
            "extraction_date": datetime.datetime.now(),
            "file_id": data.get("file_id", ""),
            "file_name": data.get("file_name", ""),
            "collection_name": data.get("collection_name", ""),
            "answers": extracted_answers,
            "total_answers": len(extracted_answers)
        }
        
        # Add paper metadata if available
        if "paper_meta" in data:
            extraction_doc["paper_meta"] = data["paper_meta"]
        
        result = db["extracted-answers"].insert_one(extraction_doc)
        extraction_id = str(result.inserted_id)
        
        # Return success result
        result = {
            "success": True,
            "extraction_id": extraction_id,
            "total_answers": len(extracted_answers)
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
    parser = argparse.ArgumentParser(description="Insert extracted answers into MongoDB")
    parser.add_argument("doc_id", help="MongoDB document ID of the original answer document")
    parser.add_argument("extraction_data", help="Extraction data JSON or file path")
    parser.add_argument("--file", action="store_true", help="Treat extraction_data as a file path")
    parser.add_argument("--matching-question-id", help="ID of the matching question document")
    
    args = parser.parse_args()
    
    # Get doc_id
    doc_id = args.doc_id
    
    # Get matching_question_id if provided
    matching_question_id = args.matching_question_id
    
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
        insert_answers(doc_id, extraction_data, matching_question_id)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Uncaught exception: {str(e)}"
        }))
        sys.exit(1) 