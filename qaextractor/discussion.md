# Implementation Discussion: AI-Powered Question Extraction Pipeline

## Current Progress ✅
1. **PDF Metadata Ingestion**  
   - Successfully writing exam papers to `pp-questions` collection with:
     ```python:extract/src/qaextractor/scripts/orchestration/process_level.py
     startLine: 87
     endLine: 108
     ```
   - Key fields established:
     - `FileID`: Unique Google Drive identifier
     - `Processed` flag: Marks extraction status
     - Full folder structure context
     - Paper metadata (Level, Subject, Year, Paper#)

2. **LLM Extraction Prototype**  
   - Demonstrated ability to extract structured questions from PDFs
   - Sample output shows successful capture of:
     - Question text & context materials
     - Image references
     - Mark allocations
     - Difficulty analysis

## Database Design Considerations 🗃️

### Proposed Collections
| Collection | Purpose | Relationship |
|------------|---------|--------------|
| `pp-questions` | Raw PDF metadata | Parent |
| `extracted-questions` | Processed questions | Child (via FileID) |
| `question-attempts` | Student responses | Grandchild (via question_id) |

### Key Relationships

mermaid
graph LR
A[pp-questions] -->|FileID| B[extracted-questions]
B -->|question_id| C[question-attempts]


1. **extracted-questions Collection**

```json
{
"exam_id": "pp-questions.FileID",
"paper_meta": {
"Level": "ASLevel",
"Subject": "English Language",
"Year": "2021",
"Paper": 3,
"Version": 31
},
"questions": [
{
"question_id": "Q3-1",
"text": "Analyse how Text A...",
"images": ["url1", "url2"],
"marks": 25,
"extraction_source": "Paper-3:31Oct.pdf"
}
]
}
```

2. **Linking Strategy**  
- Use `FileID` as primary correlation key
- Add paper metadata redundancy for faster queries
- Maintain original folder structure for auditability

## Processing Pipeline Next Steps ⚙️

### Simplified Flow
1. **Queue Identification**

```python
unprocessed = db.pp-questions.find({"Processed": False})
```


2. **PDF Processing**

- Use existing file retrieval from:
  ```python:extract/src/qaextractor/main.py
  startLine: 233
  endLine: 523
  ```
- Add LLM extraction step

3. **Data Relationships**

```python
After extraction
db.extracted-questions.insert_one({
"exam_id": original_doc["FileID"],
"paper_meta": {
"Level": original_doc["Level"],
"Subject": original_doc["Subject"],
# ... other fields
},
"questions": extracted_data
})
Mark processed
db.pp-questions.update_one(
{"FileID": original_id},
{"$set": {"Processed": True}}
)
```


## Critical Implementation Choices 🔍

1. **Denormalization vs Normalization**
- **Recommendation**: Partial denormalization
- Store paper metadata in both collections
- Pros: Faster queries, simpler code
- Cons: Slightly more storage

2. **Error Handling**
- Implement retry queue for failed extractions
- Add validation step comparing:
  ```python
  if len(extracted_questions) != expected_count:
      flag_for_review()
  ```

3. **Index Strategy**

```python
extracted-questions
db.create_index("exam_id")
db.create_index([("paper_meta.Level", 1), ("paper_meta.Subject", 1)])
```


## Roadmap Recommendations 🗺️

1. **Immediate Next Steps**
- Create `extracted-questions` collection schema
- Modify `Processed` flag handling in existing pipeline
- Implement batch processing for extraction

2. **Phase 2 Considerations**
- Add student attempt tracking
- Implement version control for LLM outputs
- Develop simple dashboard for extraction stats

3. **Long-Term**
- Add delta processing (only reprocess modified PDFs)
- Implement hot-swappable LLM providers
- Develop question similarity search

## Risk Mitigation ⚠️
1. **Data Corruption**
- Implement write-ahead logging
- Maintain PDF checksums
