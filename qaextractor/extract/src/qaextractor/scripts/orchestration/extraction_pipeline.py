import pymongo
import datetime
import os
import sys
import json
from bson.objectid import ObjectId

# Import existing functionality
from pdf_extractor import extract_pdf_content
from llm_extraction import download_pdf, extract_questions_with_llm

def connect_to_mongodb(mongodb_uri):
    """Connect to MongoDB and return database client"""
    client = pymongo.MongoClient(mongodb_uri)
    db = client["fundaAI"]
    return db

def find_unprocessed_documents(db, level=None, subject=None, year=None, batch_size=10):
    """Find unprocessed documents in pp-questions collection"""
    query = {"Processed": False, "Status": "pending"}
    
    # Add filters if provided
    if level:
        query["Level"] = level
    if subject:
        query["Subject"] = subject
    if year:
        query["Year"] = year
        
    # Find documents and limit to batch size
    return list(db["pp-questions"].find(query).limit(batch_size))

def process_document(db, document, temp_dir):
    """Process a single document with LLM extraction"""
    try:
        file_id = document["FileID"]
        file_name = document["FileName"]
        
        # Download PDF to temp directory
        pdf_path = download_pdf(file_id, file_name, temp_dir)
        
        # Extract content from PDF
        pdf_content = extract_pdf_content(pdf_path)
        
        # Use LLM to extract questions
        extracted_data = extract_questions_with_llm(pdf_content, file_name)
        
        # Create document for extracted-questions collection
        extracted_doc = {
            "exam_id": document["FileID"],
            "paper_meta": {
                "Level": document["Level"],
                "Subject": document["Subject"],
                "Year": document["Year"],
                "Paper": document["Paper"],
                "Term": document["Term"]
            },
            "questions": extracted_data["extracted_questions"],
            "total_questions": len(extracted_data["extracted_questions"]),
            "extraction_date": datetime.datetime.now()
        }
        
        # Add Version if it exists
        if "Version" in document:
            extracted_doc["paper_meta"]["Version"] = document["Version"]
            
        # Insert into extracted-questions collection
        result = db["extracted-questions"].insert_one(extracted_doc)
        
        # Update original document
        db["pp-questions"].update_one(
            {"_id": document["_id"]},
            {
                "$set": {
                    "Processed": True,
                    "ProcessedDate": datetime.datetime.now(),
                    "Status": "extracted",
                    "Metadata.TotalItems": len(extracted_data["extracted_questions"]),
                    "Metadata.LastModified": datetime.datetime.now()
                }
            }
        )
        
        return {
            "success": True,
            "document_id": str(document["_id"]),
            "extracted_id": str(result.inserted_id),
            "question_count": len(extracted_data["extracted_questions"])
        }
        
    except Exception as e:
        # Log error and update document status
        error_message = str(e)
        db["pp-questions"].update_one(
            {"_id": document["_id"]},
            {
                "$set": {
                    "Status": "error",
                    "Metadata.LastModified": datetime.datetime.now()
                },
                "$push": {
                    "ErrorLog": {
                        "timestamp": datetime.datetime.now(),
                        "message": error_message
                    }
                }
            }
        )
        
        return {
            "success": False,
            "document_id": str(document["_id"]),
            "error": error_message
        }

def process_batch(mongodb_uri, level=None, subject=None, year=None, batch_size=10):
    """Process a batch of unprocessed documents"""
    # Connect to MongoDB
    db = connect_to_mongodb(mongodb_uri)
    
    # Create temp directory for PDFs
    temp_dir = "temp_pdfs"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Find unprocessed documents
    documents = find_unprocessed_documents(db, level, subject, year, batch_size)
    
    results = {
        "total_documents": len(documents),
        "successful": 0,
        "failed": 0,
        "details": []
    }
    
    # Process each document
    for doc in documents:
        result = process_document(db, doc, temp_dir)
        results["details"].append(result)
        
        if result["success"]:
            results["successful"] += 1
        else:
            results["failed"] += 1
    
    # Clean up temp directory
    for file in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, file))
    os.rmdir(temp_dir)
    
    return results

def process_all_levels(mongodb_uri, batch_size=10):
    """Process all education levels"""
    db = connect_to_mongodb(mongodb_uri)
    
    # Get distinct levels
    levels = db["pp-questions"].distinct("Level")
    
    results = {}
    
    for level in levels:
        # Get distinct subjects for this level
        subjects = db["pp-questions"].distinct("Subject", {"Level": level})
        
        level_results = {}
        
        for subject in subjects:
            # Get distinct years for this subject
            years = db["pp-questions"].distinct("Year", {"Level": level, "Subject": subject})
            
            subject_results = {}
            
            for year in years:
                # Process this level-subject-year combination
                batch_result = process_batch(mongodb_uri, level, subject, year, batch_size)
                subject_results[year] = batch_result
            
            level_results[subject] = subject_results
        
        results[level] = level_results
    
    return results

def main():
    """Main function to run the extraction pipeline"""
    # Get MongoDB URI from environment or command line
    mongodb_uri = os.environ.get("MONGODB_URI")
    
    if len(sys.argv) > 1:
        mongodb_uri = sys.argv[1]
    
    if not mongodb_uri:
        print("Error: MongoDB URI not provided")
        sys.exit(1)
    
    # Setup MongoDB collections if they don't exist
    db = connect_to_mongodb(mongodb_uri)
    
    # Create indexes if they don't exist
    if "exam_id_1" not in db["extracted-questions"].index_information():
        db["extracted-questions"].create_index("exam_id")
    
    if "paper_meta.Level_1_paper_meta.Subject_1" not in db["extracted-questions"].index_information():
        db["extracted-questions"].create_index([("paper_meta.Level", 1), ("paper_meta.Subject", 1)])
    
    # Process documents
    if len(sys.argv) > 2 and sys.argv[2] == "all":
        # Process all levels
        results = process_all_levels(mongodb_uri)
    else:
        # Process a single batch
        results = process_batch(mongodb_uri)
    
    # Output results as JSON
    print(json.dumps(results, default=str, indent=2))

if __name__ == "__main__":
    main()
