# Final Mile Checklist

## Denormalization Explanation
**Partial denormalization** means storing some duplicated data to optimize read performance while maintaining core relationships. In your case:

mermaid
graph TD
A[pp-questions] -->|FileID| B[extracted-questions]


**Why recommend partial denormalization?**
1. **Query Efficiency**: When retrieving questions, you'll often need paper metadata (Subject/Year). Storing it with questions avoids JOIN operations.
2. **Simpler Code**: No need for multi-collection lookups
3. **Historical Preservation**: If original paper metadata changes, extracted questions retain their context
4. **Moderate Storage Impact**: Paper metadata is small compared to question content

## Implementation Checklist

### 1. Database Setup
- [ ] Create `extracted-questions` collection with schema:
  ```python:extract/src/qaextractor/scripts/orchestration/process_level.py
  startLine: 87
  endLine: 108
  ```
- [ ] Add index on `exam_id` field
- [ ] Add index on `paper_meta.Level` and `paper_meta.Subject`

### 2. Pipeline Modifications
- [ ] Add Processed flag update after extraction:
  ```python:extract/src/qaextractor/scripts/orchestration/process_level.py
  startLine: 201
  endLine: 215
  ```
- [ ] Implement batch processing for 10-20 PDFs at a time
- [ ] Add retry mechanism for failed LLM extractions

### 3. Data Relationships
- [ ] Store FileID from pp-questions as `exam_id`
- [ ] Copy these fields to extracted-questions:
  ```json
  {
    "paper_meta.Level": "ASLevel",
    "paper_meta.Subject": "English Language",
    "paper_meta.Year": "2021",
    "paper_meta.Paper": 3,
    "paper_meta.Version": 31
  }
  ```

### 4. Error Handling
- [ ] Maintain Processed=false until successful extraction
- [ ] Implement error logging matching pp-questions structure
- [ ] Add validation check:
  ```python
  if len(extracted_questions) < expected_min_questions:
      raise ValidationError
  ```

### 5. Data Corruption Prevention
- [ ] Add PDF checksum validation before processing
- [ ] Implement write-ahead logging for extraction operations

## Recommended Implementation Order
1. Database schema creation
2. Processed flag integration
3. Batch processing implementation
4. Error handling system
5. Corruption prevention measures