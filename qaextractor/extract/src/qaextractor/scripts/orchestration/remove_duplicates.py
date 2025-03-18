import pymongo
import json
import sys
import os
import re
import datetime
import argparse
from bson.objectid import ObjectId

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
    Standardize term names to "first_half" (Jan-Jun) or "second_half" (Jul-Dec)
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

def remove_duplicates_in_collection(db, collection_name, dry_run=True):
    """
    Remove duplicate documents in a collection based on metadata
    
    Args:
        db: MongoDB database connection
        collection_name: Name of the collection to clean
        dry_run: If True, only report duplicates but don't remove them
        
    Returns:
        Dictionary with results
    """
    print(f"Checking for duplicates in {collection_name}...")
    collection = db[collection_name]
    
    # Dictionary to track documents by metadata
    documents_by_metadata = {}
    
    # Track statistics
    total_docs = 0
    duplicate_groups = 0
    duplicates_found = 0
    duplicates_removed = 0
    
    # First pass: group documents by standardized metadata
    cursor = collection.find({})
    for doc in cursor:
        total_docs += 1
        
        # Get metadata from the appropriate field structure
        if collection_name in ["pp-questions", "pp-answers"]:
            # These collections have direct metadata fields
            metadata_key = (
                standardize_level(doc.get("Level", "")),
                standardize_subject(doc.get("Subject", "")),
                doc.get("Year", ""),
                doc.get("Paper", ""),
                standardize_term(doc.get("Term", ""))
            )
        elif collection_name == "extracted-questions":
            # This collection has metadata in paper_meta
            paper_meta = doc.get("paper_meta", {})
            metadata_key = (
                standardize_level(paper_meta.get("Level", "")),
                standardize_subject(paper_meta.get("Subject", "")),
                paper_meta.get("Year", ""),
                paper_meta.get("Paper", ""),
                standardize_term(paper_meta.get("Term", ""))
            )
        elif collection_name == "extracted-answers":
            # This collection typically links to questions, but might have paper_meta
            paper_meta = doc.get("paper_meta", {})
            metadata_key = (
                standardize_level(paper_meta.get("Level", "")),
                standardize_subject(paper_meta.get("Subject", "")),
                paper_meta.get("Year", ""),
                paper_meta.get("Paper", ""),
                standardize_term(paper_meta.get("Term", ""))
            )
        else:
            # Unknown collection structure
            print(f"Warning: Unknown collection structure for {collection_name}")
            continue
            
        # Skip documents with incomplete metadata (at least 3 of 5 fields should be non-empty)
        non_empty_fields = sum(1 for field in metadata_key if field)
        if non_empty_fields < 3:
            continue
            
        # Add to our tracking dictionary
        if metadata_key not in documents_by_metadata:
            documents_by_metadata[metadata_key] = []
        documents_by_metadata[metadata_key].append(doc)
    
    # Second pass: identify and remove duplicates
    for metadata_key, docs in documents_by_metadata.items():
        if len(docs) > 1:
            duplicate_groups += 1
            duplicates_found += len(docs) - 1
            
            print(f"Found {len(docs)} documents with metadata: {metadata_key}")
            
            # Sort by last modified date if available, or _id otherwise (most recent first)
            sorted_docs = sorted(docs, key=lambda d: (
                d.get("updated_at", d.get("ProcessedDate", d.get("_id"))),
            ), reverse=True)
            
            # Keep the most recently updated document, remove the others
            keep_doc = sorted_docs[0]
            docs_to_remove = sorted_docs[1:]
            
            print(f"  Keeping document {keep_doc['_id']} (most recently updated)")
            
            # Remove duplicates if not in dry run mode
            if not dry_run:
                for doc in docs_to_remove:
                    print(f"  Removing duplicate document {doc['_id']}")
                    result = collection.delete_one({"_id": doc["_id"]})
                    if result.deleted_count > 0:
                        duplicates_removed += 1
            else:
                print(f"  Would remove {len(docs_to_remove)} documents (dry run)")
                
    # Return statistics
    return {
        "collection": collection_name,
        "total_documents": total_docs,
        "duplicate_groups": duplicate_groups,
        "duplicates_found": duplicates_found,
        "duplicates_removed": 0 if dry_run else duplicates_removed,
        "dry_run": dry_run
    }

def update_metadata(db, collection_name, dry_run=True):
    """
    Update and standardize metadata fields across all documents
    
    Args:
        db: MongoDB database connection
        collection_name: Name of the collection to update
        dry_run: If True, only report changes but don't apply them
        
    Returns:
        Dictionary with results
    """
    print(f"Updating metadata in {collection_name}...")
    collection = db[collection_name]
    
    # Track statistics
    total_docs = 0
    docs_updated = 0
    
    # Process all documents
    cursor = collection.find({})
    for doc in cursor:
        total_docs += 1
        doc_id = doc["_id"]
        
        updated_fields = {}
        
        # Handle different collection structures
        if collection_name in ["pp-questions", "pp-answers"]:
            # Direct metadata fields
            if "Level" in doc:
                std_level = standardize_level(doc["Level"])
                if std_level != doc["Level"]:
                    updated_fields["Level"] = std_level
                    
            if "Subject" in doc:
                # We keep the original format but add a standardized field for matching
                updated_fields["StandardizedSubject"] = standardize_subject(doc["Subject"])
                
            if "Term" in doc:
                # We keep the original format but add a standardized field for matching
                updated_fields["StandardizedTerm"] = standardize_term(doc["Term"])
                
        elif collection_name in ["extracted-questions", "extracted-answers"]:
            # Metadata in paper_meta
            paper_meta = doc.get("paper_meta", {})
            
            if paper_meta:
                updated_meta = paper_meta.copy()
                
                if "Level" in paper_meta:
                    std_level = standardize_level(paper_meta["Level"])
                    if std_level != paper_meta["Level"]:
                        updated_meta["Level"] = std_level
                        
                if "Subject" in paper_meta:
                    # Keep original but add standardized
                    updated_meta["StandardizedSubject"] = standardize_subject(paper_meta["Subject"])
                    
                if "Term" in paper_meta:
                    # Keep original but add standardized
                    updated_meta["StandardizedTerm"] = standardize_term(paper_meta["Term"])
                    
                if updated_meta != paper_meta:
                    updated_fields["paper_meta"] = updated_meta
        
        # Add updated_at timestamp
        updated_fields["updated_at"] = datetime.datetime.now()
        
        # Apply updates if any
        if updated_fields and not dry_run:
            print(f"Updating document {doc_id} with fields: {list(updated_fields.keys())}")
            result = collection.update_one(
                {"_id": doc_id},
                {"$set": updated_fields}
            )
            if result.modified_count > 0:
                docs_updated += 1
        elif updated_fields:
            print(f"Would update document {doc_id} with fields: {list(updated_fields.keys())} (dry run)")
    
    # Return statistics
    return {
        "collection": collection_name,
        "total_documents": total_docs,
        "documents_updated": 0 if dry_run else docs_updated,
        "dry_run": dry_run
    }

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Clean duplicate documents in MongoDB collections")
    parser.add_argument("--collections", nargs="+", default=["pp-questions", "pp-answers", "extracted-questions", "extracted-answers"],
                        help="Collections to clean (default: all)")
    parser.add_argument("--update-metadata", action="store_true", help="Standardize metadata fields")
    parser.add_argument("--remove-duplicates", action="store_true", help="Remove duplicate documents")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually modify the database, just report")
    
    args = parser.parse_args()
    
    # Get MongoDB URI from environment variable
    mongodb_uri = os.environ.get("MONGODB_URI")
    if not mongodb_uri:
        print(json.dumps({"error": "MONGODB_URI environment variable not set"}))
        sys.exit(1)
    
    # Connect to MongoDB
    client = pymongo.MongoClient(mongodb_uri)
    db = client["fundaAI"]
    
    all_results = {
        "update_results": [],
        "duplicate_results": []
    }
    
    # Update metadata if requested
    if args.update_metadata:
        for collection_name in args.collections:
            result = update_metadata(db, collection_name, args.dry_run)
            all_results["update_results"].append(result)
    
    # Remove duplicates if requested
    if args.remove_duplicates:
        for collection_name in args.collections:
            result = remove_duplicates_in_collection(db, collection_name, args.dry_run)
            all_results["duplicate_results"].append(result)
    
    # Print summary
    print("\nSummary:")
    
    if args.update_metadata:
        print("\nMetadata Updates:")
        for result in all_results["update_results"]:
            print(f"  {result['collection']}: {result['documents_updated']} of {result['total_documents']} documents updated")
    
    if args.remove_duplicates:
        print("\nDuplicate Removal:")
        for result in all_results["duplicate_results"]:
            action = "Would remove" if args.dry_run else "Removed"
            print(f"  {result['collection']}: {result['duplicates_found']} duplicates in {result['duplicate_groups']} groups, {action} {result['duplicates_removed']}")
    
    # Output final JSON result
    print(json.dumps(all_results))
