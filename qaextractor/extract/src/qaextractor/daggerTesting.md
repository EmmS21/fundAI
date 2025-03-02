# Dagger Testing Plan

## Test Categories

### 1. Unit Tests

#### Google Drive Tests
- Test authentication with valid/invalid credentials
- Test listing education levels
- Test folder structure mapping
- Test paper name parsing with various formats:
  - Standard paper name: "Paper-1.pdf"
  - Paper with term: "Paper-2Oct.pdf"
  - Paper with version: "Paper-3:42.pdf"
  - Paper with term and version: "Paper-4:31Oct.pdf"
  - Handling an invalid paper name: "NotAPaper.pdf"
- Test handling of unexpected folder structures

#### MongoDB Tests
- Test connection with valid/invalid connection strings
- Test document creation with various inputs
- Test error handling for connection issues
- Test document validation and schema conformity
- Test document updates and index creation

#### Orchestration Tests
- Test processing of individual education levels
- Test document creation from the folder structure
- Test error handling during processing
- Test progress tracking across levels

#### LLM Extraction Module Tests
- Test retrieval of the PDF from MongoDB for processing
- Test that the correct extraction prompt is sent to the LLM
- Test behavior with controlled LLM responses (mocked LLM output)
- Verify extraction output includes:
  - An array of extracted questions/answers
  - The correct total count of items (questions or answers)
- Test proper error handling for:
  - Invalid PDF inputs
  - LLM prompt errors or timeouts
  - Inconsistent/partial extraction results

#### Student Performance Data Model Tests
- **(Design Validation tests since implementation is pending)**
- Validate the structure of student profiles documents:
  - Ensure required fields (e.g., student_id, name, class, demographics, created_date) exist
- Validate the structure of question attempts documents:
  - Verify fields like student_id, exam_id, question_id, attempt_data, timestamp, and attempt_type are correctly defined
- Test sample document creation against the proposed schema to ensure proper relationship keys

### 2. Integration Tests
- Test the full end-to-end flow from Google Drive file retrieval to MongoDB document creation
- Test the end-to-end flow from file ingestion → LLM-based extraction → storing the extracted output in new collections (`extracted-questions` and `extracted-answers`)
- Test handling of real folder structures in different education levels
- Test recovery from failures during each stage (Drive access, LLM extraction, database writes)
- Test performance with large datasets

### 3. Mocking Strategy
- Mock Google Drive API responses for predictable and controlled testing
- Use a MongoDB memory server or mock for database tests
- Simulate LLM responses to test extraction behavior without actual API calls
- Create fixture data for various education levels and PDF files

### 4. Test Implementation Guidelines
- Each test file should:
  - Set up necessary mocks and fixtures
  - Execute the function or module under test
  - Verify the expected outcomes including data structures and error messages
  - Clean up any resources after the test

### Example Test Cases
#### Paper Parser Tests
- Parse standard paper name: "Paper-1.pdf"
- Parse paper with term: "Paper-2Oct.pdf"
- Parse paper with version: "Paper-3:42.pdf"
- Parse paper with term and version: "Paper-4:31Oct.pdf"
- Handle invalid paper name: "NotAPaper.pdf"

#### MongoDB Document Tests
- Create document with all required fields and validate against schema
- Check proper index creation and document updates

#### Orchestration Tests
- Process level with valid structure and verify progress tracking
- Handle missing folders and report errors appropriately

#### LLM Extraction Module Tests
- Mock a PDF retrieval from MongoDB and simulate LLM processing
- Verify that the extraction JSON output contains an array of items and a correct total count field
- Test error scenarios: invalid input PDF, prompt failure, or incomplete extraction output

#### Student Performance Data Model Tests
- Validate sample document creation for student profiles with required fields
- Validate sample document creation for question attempts to ensure all necessary metadata and reference keys are present
