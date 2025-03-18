import pymongo
import json
import sys
import os
import re
import argparse

def standardize_subject(subject):
    """
    Standardize subject names by removing spaces and converting to lowercase
    """
    if not subject:
        return ""
    # Remove spaces and convert to lowercase
    return re.sub(r'\s+', '', subject).lower()

def standardize_term(term):
    """
    Standardize term names to "First Half" (Jan-Jun) or "Second Half" (Jul-Dec)
    """
    if not term:
        return ""
        
    term_lower = term.lower()
    
    # First half of year terms
    first_half = ['january', 'february', 'march', 'april', 'may', 'june', 'feb', 'mar',
                 'jan', 'apr', 'may/june', 'february/march', 'winter', 'spring']
                 
    # Second half of year terms
    second_half = ['july', 'august', 'september', 'october', 'november', 'december',
                  'jul', 'aug', 'sep', 'sept', 'oct', 'nov', 'dec', 'oct/nov', 
                  'october/november', 'october', 'summer', 'fall', 'autumn']
    
    # Check which category the term falls into
    for term_pattern in first_half:
        if term_pattern in term_lower:
            return "first_half"
            
    for term_pattern in second_half:
        if term_pattern in term_lower:
            return "second_half"
            
    # Return original if no match
    return term

def standardize_level(level):
    """
    Standardize education level
    """
    if not level:
        return ""
        
    level_lower = level.lower()
    
    if "primary" in level_lower:
        return "primary school"
    elif "as" in level_lower and ("level" in level_lower or "&" in level_lower or "and" in level_lower):
        return "aslevel"
    elif "o" in level_lower and "level" in level_lower:
        return "olevel"
        
    # Return original if no match
    return level_lower

def connect_to_mongodb(mongodb_uri):
    """Connect to MongoDB and return database client"""
    client = pymongo.MongoClient(mongodb_uri)
    db = client["fundaAI"]
    return db

def find_matching_answers(db, process_all=False, include_processed=False, limit=None, skip=0):
    """
    Find answer documents in MongoDB that have corresponding processed question documents
    
    Args:
        db: MongoDB database connection
        process_all: Whether to process all documents (ignore filter)
        include_processed: Whether to include documents already marked as processed
        limit: Maximum number of documents to return (None for all)
        skip: Number of documents to skip
        
    Returns:
        List of answer documents with matching question documents
    """
    # Build the query based on parameters
    answer_query = {
        "DocumentType": "answers"
    }
    
    # Only filter unprocessed documents if not explicitly including processed ones
    if not include_processed:
        answer_query["Processed"] = {"$ne": True}
    
    # Count total number of potential answers
    total_potential = db["pp-answers"].count_documents(answer_query)
    import logging
    logging.info(f"Total potential answer documents: {total_potential}")
    
    # Find ALL potential answers
    potential_answers = list(db["pp-answers"]
                     .find(answer_query)
                     .sort("_id", pymongo.ASCENDING)
                     .skip(skip)
                     .limit(limit if limit else 0))
    
    logging.info(f"Retrieved {len(potential_answers)} potential answers for processing")
    
    # Get all exam_ids from extracted_questions collection
    extracted_question_ids = set()
    extracted_questions_cursor = db["extracted-questions"].find({}, {"exam_id": 1, "paper_meta": 1})
    
    # Create a lookup dictionary for quick matching - using standardized keys
    extracted_question_lookup = {}
    for doc in extracted_questions_cursor:
        exam_id = doc.get("exam_id")
        if exam_id:
            meta = doc.get("paper_meta", {})
            # Create standardized key tuple
            key = (
                standardize_level(meta.get("Level", "")),
                standardize_subject(meta.get("Subject", "")),
                meta.get("Year", ""),
                meta.get("Paper", ""),
                standardize_term(meta.get("Term", ""))
            )
            extracted_question_lookup[key] = exam_id
            extracted_question_ids.add(exam_id)
    
    logging.info(f"Found {len(extracted_question_ids)} extracted questions to match against")
    
    # Filter for those with matching processed questions
    matching_answers = []
    matching_fileids = []
    
    for answer_doc in potential_answers:
        # First try matching with pp-questions collection using case-insensitive regex
        # Instead of exact match, use a more flexible approach with standardized fields
        std_level = standardize_level(answer_doc.get("Level", ""))
        std_subject = standardize_subject(answer_doc.get("Subject", ""))
        std_term = standardize_term(answer_doc.get("Term", ""))
        
        # Create regex patterns for case-insensitive matching
        level_pattern = re.compile(f"^{re.escape(answer_doc.get('Level', ''))}$", re.IGNORECASE) if answer_doc.get("Level") else None
        subject_pattern = re.compile(f"^{re.escape(answer_doc.get('Subject', ''))}$", re.IGNORECASE) if answer_doc.get("Subject") else None
        
        # Query with regex for string fields
        question_query = {
            "DocumentType": "questions",
            "Processed": True,
            "Year": answer_doc.get("Year"),
            "Paper": answer_doc.get("Paper")
        }
        
        # Add regex patterns if not None
        if level_pattern:
            question_query["Level"] = {"$regex": level_pattern}
        if subject_pattern:
            question_query["Subject"] = {"$regex": subject_pattern}
            
        # For Term, we can try exact match first and fall back to standardized approach
        if answer_doc.get("Term"):
            question_query["Term"] = {"$regex": re.compile(f"^{re.escape(answer_doc.get('Term', ''))}$", re.IGNORECASE)}
        
        # Check if matching question exists in pp-questions
        matching_question = db["pp-questions"].find_one(question_query)
        
        # Also check in extracted-questions by standardized metadata
        key = (
            std_level,
            std_subject,
            answer_doc.get("Year", ""),
            answer_doc.get("Paper", ""),
            std_term
        )
        
        # Fallback: try alternative keys with common variations
        alt_keys = []
        
        # If term matching fails, try with empty term (some entries may have blank terms)
        if std_term:
            alt_keys.append((
                std_level,
                std_subject,
                answer_doc.get("Year", ""),
                answer_doc.get("Paper", ""),
                ""
            ))
        
        # If no match, fuzzy match with just level, subject, year (ignoring paper)
        alt_keys.append((
            std_level,
            std_subject,
            answer_doc.get("Year", ""),
            "",  # Empty paper
            std_term
        ))
        
        # Try both exact and alternative keys
        match_found = False
        matched_key = None
        matched_id = None
        
        if key in extracted_question_lookup:
            match_found = True
            matched_key = key
            matched_id = extracted_question_lookup[key]
        else:
            # Try alternative keys
            for alt_key in alt_keys:
                if alt_key in extracted_question_lookup:
                    match_found = True
                    matched_key = alt_key
                    matched_id = extracted_question_lookup[alt_key]
                    break
        
        if matching_question or match_found:
            # Add question document ID for reference if from pp-questions
            if matching_question:
                answer_doc["matching_question_id"] = str(matching_question["_id"])
                answer_doc["matching_source"] = "pp-questions"
                logging.info(f"Match found in pp-questions for answer {answer_doc.get('_id')}")
            else:
                answer_doc["matching_question_id"] = matched_id
                answer_doc["matching_source"] = "extracted-questions"
                logging.info(f"Match found in extracted-questions for answer {answer_doc.get('_id')} with key {matched_key}")
                
            matching_answers.append(answer_doc)
            matching_fileids.append(answer_doc["FileID"])
    
    # Log total matches found (not print)
    logging.info(f"Found {len(matching_answers)} answers with matching processed questions")
    
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
    # Set up basic logging to stderr
    import logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    # Get MongoDB URI from environment variable
    mongodb_uri = os.environ.get("MONGODB_URI")
    if not mongodb_uri:
        print(json.dumps({"error": "MONGODB_URI environment variable not set"}))
        sys.exit(1)
    
    # Process command line arguments
    parser = argparse.ArgumentParser(description="Find answer documents with matching questions")
    parser.add_argument("--all", action="store_true", help="Process all documents")
    parser.add_argument("--include-processed", action="store_true", help="Include already processed documents")
    parser.add_argument("--skip", type=int, default=0, help="Number of documents to skip")
    parser.add_argument("--limit", type=int, help="Maximum number of documents to return")
    
    args = parser.parse_args()
    
    # Connect to MongoDB
    db = connect_to_mongodb(mongodb_uri)
    
    # Find matching answer documents
    documents, matching_fileids = find_matching_answers(
        db, 
        process_all=args.all, 
        include_processed=args.include_processed,
        limit=args.limit,
        skip=args.skip
    )
    
    # Return the JSON result
    json_result = {
        "documents": documents,
        "total_matches": len(documents),
        "matching_file_ids": matching_fileids
    }
    
    print(json.dumps(json_result))
