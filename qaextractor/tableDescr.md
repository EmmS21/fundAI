# Database Schema Design

## Existing Collections

### pp-questions
This collection stores metadata about exam papers (PDF files).

```json
{
"Level": "<ASLevel|OLevel|Primary>",
"Subject": "<subject_name>",
"Year": "<year>",
"Paper": "<paper_number>",
"Term": "<January|February|...|December>",
"Version": "<optional_version_number>",
"FileName": "<original_filename>",
"FileID": "<google_drive_file_id>",
"Processed": false,
"ProcessedDate": null,
"FolderStructure": ["path", "to", "file"],
"Questions": [],
"Metadata": {
"TotalPages": 0,
"TotalQuestions": 0,
"ExtractionDate": "<timestamp>",
"LastModified": "<timestamp>"
},
"Status": "pending",
"ErrorLog": []
}
```


## New Collections

### extracted-questions
This collection stores the actual questions extracted from exam papers using LLM.


```json
{
"id": "<ObjectId>",
"exam_id": "<reference_to_pp-questions_id>",
"paper_reference": {
"Level": "<ASLevel|OLevel|Primary>",
"Subject": "<subject_name>",
"Year": "<year>",
"Paper": "<paper_number>",
"Term": "<January|February|...|December>",
"Version": "<optional_version_number>"
},
"total_questions": 10,
"extraction_date": "<timestamp>",
"extraction_status": "<completed|failed|partial>",
"error_log": [],
"questions": [
{
    "question_id": "Q1",
"question_number": 1,
"text": "Full question text...",
"marks": 5,
"page_number": 2,
"has_image": false,
"has_table": false,
"sub_questions": [
{
"sub_id": "Q1a",
"text": "Sub-question text...",
"marks": 2
},
{
"sub_id": "Q1b",
"text": "Sub-question text...",
"marks": 3
}
],
"images": [
{
"image_id": "<unique_id>",
"caption": "Figure 1",
"base64_data": "<image_data>"
}
],
"tables": [
{
"table_id": "<unique_id>",
"caption": "Table 1",
"data": [["header1", "header2"], ["row1col1", "row1col2"]]
}
]
}
]
}
```


### extracted-answers
This collection stores answers from marking schemes extracted using LLM.

```json
{
"id": "<ObjectId>",
"exam_id": "<reference_to_pp-questions_id>",
"paper_reference": {
"Level": "<ASLevel|OLevel|Primary>",
"Subject": "<subject_name>",
"Year": "<year>",
"Paper": "<paper_number>",
"Term": "<January|February|...|December>",
"Version": "<optional_version_number>"
},
"total_answers": 10,
"extraction_date": "<timestamp>",
"extraction_status": "<completed|failed|partial>",
"error_log": [],
"answers": [
{
"question_id": "Q1",
"answer_text": "Full answer text...",
"total_marks": 5,
"marking_points": [
{
    "point_id": "P1",
"description": "Point description",
"marks": 1
},
{
"point_id": "P2",
"description": "Point description",
"marks": 2
}
],
"sub_answers": [
{
"sub_id": "Q1a",
"answer_text": "Answer to sub-question...",
"marks": 2,
"marking_points": [] }],
    "examples": [
    {
    "text": "Example of a correct answer",
    "marks_awarded": 5    
    }
]}]}


### student-profiles
This collection stores information about students.

```json
json
{
"id": "<ObjectId>",
"student_id": "<unique_student_id>",
"name": {
"first": "<first_name>",
"last": "<last_name>"
},
"email": "<email_address>",
"class": "<class_code>",
"year_group": "<year_group>",
"school": "<school_name>",
"demographics": {
"age": "<age>",
"gender": "<gender>"
},
"created_date": "<timestamp>",
"last_active": "<timestamp>"
}
```

### question-attempts
This collection stores information about student attempts at questions.

```json
json
{
"id": "<ObjectId>",
"student_id": "<reference_to_student-profiles_id>",
"exam_id": "<reference_to_pp-questions_id>",
"question_id": "<reference_to_question_in_extracted-questions>",
"attempt_type": "<practice|test|exam>",
"timestamp": "<timestamp>",
"time_spent": "<seconds>",
"answer_text": "Student's answer text...",
"answer_images": [
{
"image_id": "<unique_id>",
"base64_data": "<image_data>"
}
],
"marks_awarded": 3,
"max_marks": 5,
"feedback": {
"auto_generated": "Feedback text from LLM...",
"teacher": "Teacher's feedback..."
},
"marking_points_achieved": ["P1", "P2"],
"confidence_level": "<student_reported_confidence>",
"llm_assessment": {
"accuracy": 0.75,
"completeness": 0.8,
"misconceptions": ["Description of misconception"],
"suggestions": ["Suggestion for improvement"]
}
}
```


## Relationships Between Collections

1. **pp-questions → extracted-questions**:
   - The `exam_id` in extracted-questions references the `_id` in pp-questions
   - When questions are extracted, the `Metadata.TotalQuestions` field in pp-questions is updated
   - The `Status` field in pp-questions is updated to "extracted" once LLM extraction is complete
   - The `ProcessedDate` field in pp-questions is updated with the timestamp

2. **pp-questions → extracted-answers**:
   - The `exam_id` in extracted-answers references the `_id` in pp-questions
   - Similar updates happen to the pp-questions collection status fields

3. **extracted-questions → question-attempts**:
   - The `question_id` in question-attempts references the specific question in extracted-questions
   - This allows tracking which specific questions students have attempted

4. **student-profiles → question-attempts**:
   - The `student_id` in question-attempts references the `_id` in student-profiles
   - This allows tracking all attempts made by a specific student

## Processing Flow

1. PDF exam papers are initially ingested and stored in the pp-questions collection
2. LLM extraction processes these PDFs to extract individual questions and answers
3. Extracted questions are stored in the extracted-questions collection
4. Extracted answers are stored in the extracted-answers collection
5. Students can attempt questions, with their answers stored in question-attempts
6. Analytics can be generated based on the relationships between these collections

## Indexing Strategy

- pp-questions: Indexes on (Level, Subject, Year, Paper, Term)
- extracted-questions: Indexes on exam_id and question_id
- extracted-answers: Indexes on exam_id and question_id
- student-profiles: Indexes on student_id and email
- question-attempts: Indexes on student_id, exam_id, and question_id

## Data Storage Options for Images and Tables

### Option 1: MongoDB GridFS
**Description:** GridFS is MongoDB's solution for storing files larger than the 16MB document size limit. It works by splitting files into chunks and storing them in a separate collection.

**Pros:**
- Built directly into MongoDB (no additional services required)
- Simplifies architecture by keeping all data in one system
- No additional cost beyond existing MongoDB instance
- Automatic chunking of large files
- Consistent backup strategy with the rest of the database

**Cons:**
- Can significantly increase MongoDB storage usage
- Not as optimized for serving images as dedicated object storage
- Potential performance impact with many large files
- Less efficient for high-traffic image serving

### Option 2: AWS S3 or Similar Object Storage
**Description:** Cloud object storage services like AWS S3, Google Cloud Storage, or Azure Blob Storage are purpose-built for storing and serving binary objects.

**Pros:**
- Highly scalable and optimized for object storage
- Excellent performance for serving images
- Strong durability and availability guarantees
- Can integrate with CDNs for faster delivery
- Cost-effective for large storage needs

**Cons:**
- Additional service to manage
- Not free (though cost-effective)
  - AWS S3 free tier: 5GB for 12 months
  - Google Cloud Storage free tier: 5GB permanently
- Requires additional authentication and configuration
- Slightly more complex architecture

### Option 3: Google Drive (Current System)
**Description:** Since the application already uses Google Drive for PDF storage, it could also be used for extracted images.

**Pros:**
- Already integrated into the system
- Familiar API
- Some free storage available
- No need to set up additional services

**Cons:**
- Not designed as an object store for application data
- API might be slower than dedicated object storage
- Usage quotas and potential rate limiting
- More complex permissions model than needed

### Recommended Approach
For this application, a hybrid approach is recommended:

1. **Initial Implementation (Small Scale):**
   - Use MongoDB GridFS for simplicity during development and initial deployment
   - Store smaller images and tables directly in the MongoDB documents as Base64 strings (for items under ~1MB)
   - This approach minimizes architectural complexity

2. **Growth Phase:**
   - Migrate to Google Cloud Storage or AWS S3 as image volume increases
   - Store only references to images in MongoDB
   - Schema structure already supports this transition with minimal changes

3. **Storage Implementation in Schema:**
   ```json
   // For GridFS approach (initial)
   "images": [
     {
       "image_id": "<gridfs_file_id>",
       "caption": "Figure 1"
     }
   ]

   // For cloud storage approach (growth phase)
   "images": [
     {
       "image_id": "<unique_id>",
       "caption": "Figure 1",
       "storage_url": "https://storage.googleapis.com/bucket/image.png"
     }
   ]
   ```

This approach allows starting with a simpler architecture while providing a clear path for scaling as the application grows.


```bash
dagger call orchestrate \
  --credentials-json file:///Users/ripplingadmin/Documents/GitHub/fundAI/qaextractor/extract/credentials.json \
  --connection-string env://MONGODB_URI
```
