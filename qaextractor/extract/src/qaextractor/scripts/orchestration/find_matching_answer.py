import pymongo
import json
import sys
import os

def connect_to_mongodb(mongodb_uri):
    """Connect to MongoDB and return database client"""
    client = pymongo.MongoClient(mongodb_uri)
    db = client["fundaAI"]
    return db

def find_matching_answers(db, process_all=False, limit=None, skip=0):
    """
    Find ALL unprocessed answer documents in MongoDB that have corresponding processed question documents
    
    Args:
        db: MongoDB database connection
        process_all: Whether to process all documents (ignore filter)
        limit: Maximum number of documents to return (None for all)
        skip: Number of documents to skip
        
    Returns:
        List of unprocessed answer documents with matching question documents
    """
    # Start with unprocessed answers
    answer_query = {
        "DocumentType": "answers",
        "Processed": {"$ne": True}
    }
    
    # Count total number of potential answers
    total_potential = db["pp-answers"].count_documents(answer_query)
    print(f"Total unprocessed answer documents: {total_potential}")
    
    # Find ALL potential answers by setting limit to 0
    # This approach might be slow for very large collections but gives us full count
    potential_answers = list(db["pp-answers"]
                     .find(answer_query)
                     .sort("_id", pymongo.ASCENDING))
    
    print(f"Retrieved {len(potential_answers)} potential answers for processing")
    
    # Get all exam_ids from extracted_questions collection
    extracted_question_ids = set()
    extracted_questions_cursor = db["extracted-questions"].find({}, {"exam_id": 1, "paper_meta": 1})
    
    # Create a lookup dictionary for quick matching
    extracted_question_lookup = {}
    for doc in extracted_questions_cursor:
        exam_id = doc.get("exam_id")
        if exam_id:
            meta = doc.get("paper_meta", {})
            key = (
                meta.get("Level", ""),
                meta.get("Subject", ""),
                meta.get("Year", ""),
                meta.get("Paper", ""),
                meta.get("Term", "")
            )
            extracted_question_lookup[key] = exam_id
            extracted_question_ids.add(exam_id)
    
    print(f"Found {len(extracted_question_ids)} extracted questions to match against")
    
    # Filter for those with matching processed questions
    matching_answers = []
    matching_fileids = []
    
    for answer_doc in potential_answers:
        # First try matching with pp-questions collection
        question_query = {
            "DocumentType": "questions",
            "Processed": True,
            "Level": answer_doc.get("Level"),
            "Subject": answer_doc.get("Subject"),
            "Year": answer_doc.get("Year"),
            "Paper": answer_doc.get("Paper"),
            "Term": answer_doc.get("Term")
        }
        
        # Check if matching question exists in pp-questions
        matching_question = db["pp-questions"].find_one(question_query)
        
        # Also check in extracted-questions by metadata
        key = (
            answer_doc.get("Level", ""),
            answer_doc.get("Subject", ""),
            answer_doc.get("Year", ""),
            answer_doc.get("Paper", ""),
            answer_doc.get("Term", "")
        )
        
        if matching_question or key in extracted_question_lookup:
            # Add question document ID for reference if from pp-questions
            if matching_question:
                answer_doc["matching_question_id"] = str(matching_question["_id"])
                answer_doc["matching_source"] = "pp-questions"
            else:
                answer_doc["matching_question_id"] = extracted_question_lookup[key]
                answer_doc["matching_source"] = "extracted-questions"
                
            matching_answers.append(answer_doc)
            matching_fileids.append(answer_doc["FileID"])
    
    # Print total matches found
    print(f"Found {len(matching_answers)} answers with matching processed questions")
    
    # Format result for output
    result = []
    for doc in matching_answers:
        doc_info = {
            "_id": str(doc["_id"]),
            "FileID": doc["FileID"],
            "FileName": doc.get("FileName", "Unknown"),
            "Level": doc.get("Level", ""),
            "Subject": doc.get("Subject", ""),
            "Year": doc.get("Year", ""),
            "Paper": doc.get("Paper", ""),
            "Term": doc.get("Term", ""),
            "matching_question_id": doc.get("matching_question_id", ""),
            "matching_source": doc.get("matching_source", "")
        }
        result.append(doc_info)
    
    return result, matching_fileids

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
    
    # Find matching answer documents - removing the limit to get all matches
    documents, matching_fileids = find_matching_answers(db, process_all, None, skip)
    
    # Return as JSON
    print(json.dumps({
        "documents": documents[:10],  # Only show first 10 for brevity in output
        "total_matches": len(documents),
        "matching_file_ids": matching_fileids
    }, indent=2))
