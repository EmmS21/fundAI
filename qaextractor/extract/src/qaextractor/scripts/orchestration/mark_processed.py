import sys
import os
import json
import pymongo
import datetime
from bson.objectid import ObjectId
import argparse

def mark_as_processed(doc_id, collection_name="pp-questions", extraction_id=None, total_items=0, related_doc_id=None):
    """
    Mark a document as processed in the specified collection
    
    Args:
        doc_id: MongoDB document ID
        collection_name: Collection name ("pp-questions" or "pp-answers")
        extraction_id: ID of the extracted document (optional)
        total_items: Total number of items extracted (questions or answers)
        related_doc_id: ID of related document (matching question for answers, or vice versa)
    """
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient(os.environ.get("MONGODB_URI"))
        db = client["fundaAI"]
        
        # Check if document exists
        doc = db[collection_name].find_one({"_id": ObjectId(doc_id)})
        if not doc:
            return {"success": False, "error": f"Document {doc_id} not found in {collection_name}"}
        
        # Prepare the update
        update_doc = {
            "Processed": True,
            "ProcessedDate": datetime.datetime.now(),
            "Status": "Extracted"
        }
        
        # Add metadata if available
        metadata = {}
        
        # Set the appropriate field name based on collection
        if total_items > 0:
            field_name = "TotalQuestionsExtracted" if collection_name == "pp-questions" else "TotalAnswersExtracted"
            metadata[field_name] = total_items
            
        if extraction_id:
            metadata["ExtractionId"] = extraction_id
            
        if related_doc_id:
            relation_field = "MatchingAnswerId" if collection_name == "pp-questions" else "MatchingQuestionId"
            metadata[relation_field] = related_doc_id
        
        if metadata:
            # Update the metadata field if it exists, otherwise create it
            update_doc["Metadata"] = {
                **doc.get("Metadata", {}),
                **metadata,
                "LastModified": datetime.datetime.now()
            }
        
        # Update the document
        result = db[collection_name].update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": update_doc}
        )
        
        return {
            "success": result.modified_count > 0,
            "document_id": doc_id,
            "collection": collection_name,
            "matched_count": result.matched_count,
            "modified_count": result.modified_count
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Mark a document as processed")
    parser.add_argument("doc_id", help="MongoDB document ID")
    parser.add_argument("--collection", default="pp-questions", choices=["pp-questions", "pp-answers"],
                        help="Collection name (pp-questions or pp-answers)")
    parser.add_argument("--extraction-id", help="ID of the extracted document")
    parser.add_argument("--total-items", type=int, default=0, help="Total number of items extracted")
    parser.add_argument("--related-doc-id", help="ID of related document (matching question/answer)")
    
    args = parser.parse_args()
    
    # Call the main function
    result = mark_as_processed(
        args.doc_id,
        args.collection,
        args.extraction_id,
        args.total_items,
        args.related_doc_id
    )
    
    # Print result as JSON
    print(json.dumps(result))
