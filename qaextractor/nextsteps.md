# Technical Requirements for Answer Extraction Pipeline

## Overview

We need to build a parallel extraction pipeline that processes answer documents (marking schemes) from the `pp-answers` collection in MongoDB, but only for those papers that have corresponding question papers already processed in the `pp-questions` collection. This ensures we only focus our extraction efforts on complete question-answer pairs.

## Current System Architecture

The existing system uses Dagger to orchestrate containers that:
1. Find unprocessed documents in MongoDB
2. Download PDFs from Google Drive
3. Extract text and images from PDFs
4. Use LLM processing to extract structured question data
5. Insert processed data back into MongoDB
6. Mark documents as processed

## Technical Requirements for Answer Extraction

### 1. New Dagger Module

We'll create a new function in the existing `Qaextractor` class called `extract_answers` that follows a similar pattern to the existing `run` function but with specific modifications for answer processing:

```python
@function
async def extract_answers(self, mongodb_uri: Secret, credentials_json: Secret, process_all: bool = False) -> str:
    """
    Runs the extraction pipeline to process unprocessed answer documents in MongoDB,
    but only for those that have corresponding processed question documents.
    """
    # Implementation details here
```

### 2. Cross-Reference Logic

We need to implement logic that:
1. Queries `pp-answers` for unprocessed documents
2. For each document, checks if there's a corresponding document in `pp-questions` that has been processed
3. Only processes answer documents that match processed question documents

The matching logic should compare:
- Level (e.g., "Primary School", "ASLevel")
- Subject (e.g., "Science", "English Language")
- Term (e.g., "January", "October")
- Year (e.g., "2014", "2021")
- Paper number (e.g., 2, 3)

### 3. MongoDB Query Strategy

We'll create a new script `find_matching_answers.py` that implements this cross-reference logic:

```python
def find_matching_answers(db, process_all=False, limit=10, skip=0):
    """
    Find unprocessed answer documents in MongoDB that have corresponding processed question documents
    
    Args:
        db: MongoDB database connection
        process_all: Whether to process all documents (ignore filter)
        limit: Maximum number of documents to return
        skip: Number of documents to skip
        
    Returns:
        List of unprocessed answer documents with matching question documents
    """
    # Start with unprocessed answers
    answer_query = {
        "DocumentType": "answers",
        "Processed": {"$ne": True}
    }
    
    # Find potential answers
    potential_answers = list(db["pp-answers"]
                     .find(answer_query)
                     .sort("_id", pymongo.ASCENDING)
                     .skip(skip)
                     .limit(limit))
    
    # Filter for those with matching processed questions
    matching_answers = []
    for answer_doc in potential_answers:
        # Query to find matching question document
        question_query = {
            "DocumentType": "questions",
            "Processed": True,
            "Level": answer_doc.get("Level"),
            "Subject": answer_doc.get("Subject"),
            "Year": answer_doc.get("Year"),
            "Paper": answer_doc.get("Paper"),
            "Term": answer_doc.get("Term")
        }
        
        # Check if matching question exists
        matching_question = db["pp-questions"].find_one(question_query)
        
        if matching_question:
            # Add question document ID for reference
            answer_doc["matching_question_id"] = str(matching_question["_id"])
            matching_answers.append(answer_doc)
    
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
            "matching_question_id": doc.get("matching_question_id", "")
        }
        result.append(doc_info)
    
    return result
```

### 4. Answer Extraction Prompt

We'll need to adapt the existing LLM prompt for extracting answers instead of questions. The key differences:

```python
answer_extractor = (
    dag.llm()
    .with_prompt(f"""
    The following text is from an exam marking scheme/answer paper:
    
    {pdf_text_data['text']}
    
    Analyze this text and extract ALL answers in the marking scheme, maintaining the question numbering from the original exam paper. For each answer:
    
    1. Identify the question/sub-question number (must match the original exam paper)
    2. Extract the complete answer text/marking criteria
    3. Note the marks allocated for each part of the answer
    4. Include any alternative acceptable answers
    5. Identify marking rubrics or grading schemes
    6. Note any specific instructions for markers
    
    IMPORTANT: Many marking schemes include explanatory notes, worked examples, or sample answers that should be preserved in full.
    
    Return ONLY a JSON object with this structure:
    {{
      "total_questions": 5,
      "answers": [
        {{
          "question_number": 1,
          "answer_text": "Full text of the model answer/marking criteria",
          "marking_scheme": {{
            "total_marks": 15,
            "grade_boundaries": {{
              "description": "Description of how marks correspond to grades if provided"
            }}
          }},
          "sub_answers": [
            {{
              "sub_number": "a",
              "text": "Text of answer to sub-question a",
              "marks": 5,
              "alternatives": ["Alternative acceptable answer 1", "Alternative acceptable answer 2"],
              "marking_notes": "Any specific notes for markers about this question"
            }}
          ]
        }}
      ]
    }}
    
    No other text or formatting.
    """)
)
```

### 5. Data Storage Structure

We'll need to create a new collection schema for storing extracted answers:

```python
answer_doc = {
    "document_id": doc_id,                    # The original answer document ID
    "question_document_id": matching_question_id,  # The ID of the matching question document
    "extraction_date": datetime.datetime.now(),
    "file_id": data.get("file_id", ""),
    "file_name": data.get("file_name", ""),
    "level": answer_doc.get("Level", ""),
    "subject": answer_doc.get("Subject", ""),
    "year": answer_doc.get("Year", ""),
    "paper": answer_doc.get("Paper", ""),
    "term": answer_doc.get("Term", ""),
    "answers": extracted_answers,
    "total_answers": len(extracted_answers)
}
```

### 6. New Helper Scripts

We'll need to create several new scripts:

1. `find_matching_answers.py` - For finding answer documents with matching question documents
2. `insert_answers.py` - For inserting extracted answers into MongoDB
3. `mark_answer_processed.py` - For marking answer documents as processed

These will follow the same patterns as the existing scripts but with adaptations for answer processing.

## Technical Considerations

### 1. Dagger Container Optimization

To fully utilize Dagger's caching mechanism:

1. Separate logic into discrete container operations:
   - Finding documents
   - Downloading PDFs
   - Extracting text
   - Processing with LLM
   - Storing results
   
2. Ensure deterministic inputs for each container to maximize cache hits:
   - Use stable sorting in MongoDB queries
   - Use consistent parameter ordering
   - Minimize environment variations between runs

3. Keep container definitions identical for similar operations to leverage caching

### 2. Error Handling and Robustness

1. Implement comprehensive error handling at each stage:
   - MongoDB connection issues
   - PDF download failures
   - Text extraction errors
   - LLM processing failures
   - JSON parsing errors

2. Track processing statistics for monitoring:
   - Total documents processed
   - Success rate
   - Failure categories
   - Processing time

3. Implement retries for intermittent failures with exponential backoff

### 3. Memory Management

Given the previous OOM (Out of Memory) issues:

1. Process documents in small batches (10 documents at a time)
2. Implement delay between batches to allow for garbage collection
3. Monitor memory usage during processing
4. Consider lower-memory alternatives for PDF processing if possible

### 4. Cross-Collection Transaction Safety

When dealing with two related collections:

1. Use atomic updates where possible
2. Implement idempotent operations to handle retry scenarios
3. Store relationship between question and answer documents in both collections
4. Consider implementing a transaction-like pattern for updates spanning collections

## Implementation Plan

### 1. Create New Scripts

First, create the necessary new scripts:

- `find_matching_answers.py`
- `insert_answers.py`
- `mark_answer_processed.py`

### 2. Add New Function to Qaextractor

Add the `extract_answers` function to the existing `Qaextractor` class in `main.py`.

### 3. Adapt LLM Prompt

Modify the existing LLM prompt to extract answer information rather than questions.

### 4. Implement Document Matching Logic

Create the cross-reference logic to match answer documents with their corresponding question documents.

### 5. Create Answer Storage Structure

Implement the appropriate data structure for storing extracted answers in MongoDB.

### 6. Test with Sample Documents

Test the pipeline with a small sample of documents to validate the extraction process.

### 7. Monitor and Optimize

Monitor performance and optimize for:
- Memory usage
- Processing speed
- Success rate
- Failure modes

## Final Notes

The implementation should maintain consistency with the existing codebase while adding new functionality for answer extraction. By leveraging the existing patterns and components, we can minimize development time and ensure reliability.

The main focus should be on:
1. Correctly matching answer documents with their question counterparts
2. Adapting the extraction prompt to properly identify answer content
3. Maintaining robust error handling and monitoring
4. Ensuring efficient use of computing resources
