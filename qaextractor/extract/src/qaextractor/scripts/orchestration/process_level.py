import json
import re
import datetime
import os
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pymongo
import constants

def get_drive_service():
    """Create and return an authorized Google Drive service instance"""
    credentials = service_account.Credentials.from_service_account_file(
        "credentials.json",
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=credentials)

def get_folder_contents(service, folder_id, include_files=False):
    """Get contents of a Google Drive folder"""
    query = f"'{folder_id}' in parents and trashed = false"
    if not include_files:
        query += " and mimeType = 'application/vnd.google-apps.folder'"
    
    results = service.files().list(
        q=query,
        fields="files(id, name, mimeType)"
    ).execute()
    return results.get("files", [])

def get_exam_folder(service, subject_id, level_name):
    """Find the exams folder based on education level"""
    folders = get_folder_contents(service, subject_id)
    target_folder = "Exams" if level_name in ["ASLevel", "OLevel"] else "PP"
    for folder in folders:
        if folder["name"] == target_folder:
            return folder
    return None

def parse_paper_name(filename):
    """Parse paper name to extract paper number, term, and version"""
    # Remove .pdf extension
    if filename.lower().endswith(".pdf"):
        filename = filename[:-4]
    
    # Default values
    paper_info = {
        "paper": None,
        "term": "January",
        "version": None
    }
    
    # Extract version if present (format: Paper-1:42.pdf or Paper-2:31Oct.pdf)
    version_match = re.search(r':(\d+)', filename)
    if version_match:
        paper_info["version"] = int(version_match.group(1))
        # Remove version part for further processing
        filename = re.sub(r':\d+', '', filename)
    
    # Extract paper number (required)
    paper_match = re.search(r'(\d+)', filename)
    if paper_match:
        paper_info["paper"] = int(paper_match.group(1))
    else:
        return None  # Invalid paper name
    
    # Extract term if present
    month_pattern = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
    month_match = re.search(month_pattern, filename)
    if month_match:
        month_abbr = month_match.group(1)
        months = {
            "Jan": "January", "Feb": "February", "Mar": "March",
            "Apr": "April", "May": "May", "Jun": "June",
            "Jul": "July", "Aug": "August", "Sep": "September",
            "Oct": "October", "Nov": "November", "Dec": "December"
        }
        paper_info["term"] = months.get(month_abbr, "January")
    
    return paper_info

def create_document(level_name, subject, year, paper_info, folder_path, doc_type):
    """Create a MongoDB document for a paper or marking scheme"""
    now = datetime.datetime.now()
    
    # Create document
    document = {
        "Level": level_name,
        "Subject": subject["name"],
        "Year": year["name"],
        "Paper": paper_info["paper"],
        "Term": paper_info["term"],
        "FileName": paper_info["name"],
        "FileID": paper_info["id"],
        "Processed": False,
        "ProcessedDate": None,
        "FolderStructure": folder_path,
        "DocumentType": doc_type,  # "questions" or "answers"
        "Content": [],  # Will be "Questions" or "Answers" based on type
        "Metadata": {
            "TotalPages": 0,
            "TotalItems": 0,  # Will be questions or answers count
            "ExtractionDate": now,
            "LastModified": now
        },
        "Status": "pending",
        "ErrorLog": []
    }
    
    # Add version if present
    if paper_info.get("version") is not None:
        document["Version"] = paper_info["version"]
    
    return document

def navigate_to_papers(service, level_name, subject_id):
    """Navigate to papers based on education level structure"""
    if level_name in ["ASLevel", "OLevel"]:
        # Find Exams folder
        folders = get_folder_contents(service, subject_id)
        exam_folder = None
        for folder in folders:
            if folder["name"] == "Exams":
                exam_folder = folder
                break
        
        if not exam_folder:
            return []
            
        # Get years
        years = get_folder_contents(service, exam_folder["id"])
        
        # Collect papers from all years
        all_papers = []
        for year in years:
            papers = get_folder_contents(service, year["id"], True)
            papers = [p for p in papers if p["name"].lower().endswith(".pdf")]
            for paper in papers:
                all_papers.append({
                    "paper": paper,
                    "year": year,
                    "exam_folder": exam_folder,
                    "subject_id": subject_id
                })
        
        return all_papers
    else:
        # Primary School structure
        years = get_folder_contents(service, subject_id)
        
        all_papers = []
        for year in years:
            # Find PP folder
            folders = get_folder_contents(service, year["id"])
            pp_folder = None
            for folder in folders:
                if folder["name"] == "PP":
                    pp_folder = folder
                    break
            
            if not pp_folder:
                continue
                
            # Get papers
            papers = get_folder_contents(service, pp_folder["id"], True)
            papers = [p for p in papers if p["name"].lower().endswith(".pdf")]
            for paper in papers:
                all_papers.append({
                    "paper": paper,
                    "year": year,
                    "pp_folder": pp_folder,
                    "subject_id": subject_id
                })
        
        return all_papers

def process_level(level_name, level_id, mongodb_uri):
    """Process a single education level and create MongoDB documents for both questions and answers"""
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient(mongodb_uri)
        db = client["fundaAI"]
        questions_collection = db["pp-questions"]
        answers_collection = db["pp-answers"]
        
        documents_created = 0
        errors = 0
        error_details = []
        
        # Get Drive service
        service = get_drive_service()
        
        # Get subjects in this level
        subjects = get_folder_contents(service, level_id)
        
        for subject in subjects:
            if level_name in ["ASLevel", "OLevel"]:
                # Process exam papers (questions)
                exam_folder = find_folder(service, subject["id"], "Exams")
                if exam_folder:
                    documents_created += process_folder_structure(
                        service, level_name, subject, exam_folder, 
                        questions_collection, "questions", error_details
                    )
                
                # Process marking schemes (answers) - try both naming conventions
                ms_folder = find_folder(service, subject["id"], "MS")
                if not ms_folder:
                    ms_folder = find_folder(service, subject["id"], "Marking Schema")
                
                if ms_folder:
                    documents_created += process_folder_structure(
                        service, level_name, subject, ms_folder, 
                        answers_collection, "answers", error_details
                    )
            else:
                # Primary School structure: Level → Subjects → Years → (PP|MS) → Papers
                years = get_folder_contents(service, subject["id"])
                
                for year in years:
                    # Process past papers (questions)
                    pp_folder = find_folder(service, year["id"], "PP")
                    if pp_folder:
                        documents_created += process_primary_folder(
                            service, level_name, subject, year, pp_folder, 
                            questions_collection, "questions", error_details
                        )
                    
                    # Process marking schemes (answers)
                    ms_folder = find_folder(service, year["id"], "MS")
                    if ms_folder:
                        documents_created += process_primary_folder(
                            service, level_name, subject, year, ms_folder, 
                            answers_collection, "answers", error_details
                        )
        
        # Create result
        return constants.create_level_result(
            level_name,
            documents_created,
            len(error_details),
            error_details[:5]  # Limit error details to first 5
        )
        
    except Exception as e:
        return constants.create_level_result(
            level_name,
            0,
            1,
            [f"Failed to process level: {str(e)}"]
        )

def find_folder(service, parent_id, folder_name_patterns):
    """
    Find a folder that matches any of the given name patterns
    
    Args:
        service: Google Drive service
        parent_id: ID of the parent folder
        folder_name_patterns: String or list of strings with possible folder names
    
    Returns:
        Folder dict or None if not found
    """
    if isinstance(folder_name_patterns, str):
        folder_name_patterns = [folder_name_patterns]
        
    folders = get_folder_contents(service, parent_id)
    
    # First try exact matches
    for folder in folders:
        for pattern in folder_name_patterns:
            if folder["name"].lower() == pattern.lower():
                return folder
    
    # Then try partial matches
    for folder in folders:
        for pattern in folder_name_patterns:
            if pattern.lower() in folder["name"].lower():
                return folder
    
    return None

def process_folder_structure(service, level_name, subject, folder, collection, doc_type, error_details):
    """Process ASLevel/OLevel folder structure and create documents"""
    documents_created = 0
    
    # Get years in this folder
    years = get_folder_contents(service, folder["id"])
    
    for year in years:
        # Get papers in this year
        papers = get_folder_contents(service, year["id"], True)
        papers = [p for p in papers if p["name"].lower().endswith(".pdf")]
        
        for paper in papers:
            try:
                # Parse paper name
                paper_info = parse_paper_name(paper["name"])
                if not paper_info:
                    error_details.append(f"Invalid paper name: {paper['name']}")
                    continue
                    
                # Add file info to paper_info
                paper_info["id"] = paper["id"]
                paper_info["name"] = paper["name"]
                
                # Create folder path
                folder_path = [
                    level_name, 
                    subject["name"], 
                    folder["name"], 
                    year["name"], 
                    paper["name"]
                ]
                
                # Create document
                document = create_document(level_name, subject, year, paper_info, folder_path, doc_type)
                
                # Insert into MongoDB
                result = collection.update_one(
                    {"FileID": paper_info["id"]},
                    {"$set": document},
                    upsert=True
                )
                
                if result.upserted_id or result.modified_count > 0:
                    documents_created += 1
                
            except Exception as e:
                error_details.append(f"Error processing {paper['name']}: {str(e)}")
    
    return documents_created

def process_primary_folder(service, level_name, subject, year, folder, collection, doc_type, error_details):
    """Process Primary School folder structure and create documents"""
    documents_created = 0
    
    # Get papers in this folder
    papers = get_folder_contents(service, folder["id"], True)
    papers = [p for p in papers if p["name"].lower().endswith(".pdf")]
    
    for paper in papers:
        try:
            # Parse paper name
            paper_info = parse_paper_name(paper["name"])
            if not paper_info:
                error_details.append(f"Invalid paper name: {paper['name']}")
                continue
                
            # Add file info to paper_info
            paper_info["id"] = paper["id"]
            paper_info["name"] = paper["name"]
            
            # Create folder path
            folder_path = [
                level_name, 
                subject["name"], 
                year["name"], 
                folder["name"], 
                paper["name"]
            ]
            
            # Create document
            document = create_document(level_name, subject, year, paper_info, folder_path, doc_type)
            
            # Insert into MongoDB
            result = collection.update_one(
                {"FileID": paper_info["id"]},
                {"$set": document},
                upsert=True
            )
            
            if result.upserted_id or result.modified_count > 0:
                documents_created += 1
            
        except Exception as e:
            error_details.append(f"Error processing {paper['name']}: {str(e)}")
    
    return documents_created

if __name__ == "__main__":
    # Get arguments
    if len(sys.argv) < 3:
        print(json.dumps({
            "error": "Missing required arguments: level_name, level_id, mongodb_uri"
        }))
        sys.exit(1)
        
    level_name = sys.argv[1]
    level_id = sys.argv[2]
    mongodb_uri = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("MONGODB_URI")
    
    if not mongodb_uri:
        print(json.dumps({
            "error": "MongoDB URI not provided"
        }))
        sys.exit(1)
    
    # Process the level
    result = process_level(level_name, level_id, mongodb_uri)
    
    # Output result as JSON
    print(json.dumps(result))
