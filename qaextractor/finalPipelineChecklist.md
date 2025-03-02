# Final Pipeline Checklist

## 1. LLM-Based Extraction Integration
- [ ] **Design Extraction Prompts**
  - [ ] Define a clear prompt for exam paper (questions) extraction.
  - [ ] Define a clear prompt for marking scheme (answers) extraction.
- [ ] **Develop LLM Extraction Module**
  - [ ] Create a new file: `src/qaextractor/scripts/orchestration/llm_extraction.py`
  - [ ] Implement functionality to retrieve the PDF from MongoDB.
  - [ ] Implement functionality to send the PDF with the prompt to the LLM.
  - [ ] Process and validate the output from the LLM (ensure the question/answer count is correct).
  - [ ] Store the extracted JSON output into new collections: `extracted-questions` and `extracted-answers`.
- [ ] **Integration**
  - [ ] Integrate the LLM extraction module into the existing orchestration pipeline.
  - [ ] Update the pipeline to trigger LLM extraction after file ingestion.

## 2. Student Performance Data Model Design
- [ ] **Design Student Profiles Collection**
  - [ ] Define required fields (e.g., student_id, name, class, demographics, created_date).
  - [ ] Finalize and document the data model.
- [ ] **Design Question Attempts Collection**
  - [ ] Define required fields (e.g., student_id, exam_id, question_id, attempt_data, timestamp, attempt_type).
  - [ ] Outline relationships with the extracted questions.
- [ ] **Documentation & Review**
  - [ ] Update the design documentation (e.g., `newDBdesign.md`) with the student performance models.
  - [ ] Conduct a design review with the team.

## 3. Testing and Quality Assurance for New Features
- [ ] **LLM Extraction Module Testing**
  - [ ] Write unit tests for the LLM extraction functions (valid PDF inputs, correct extraction output).
  - [ ] Test error handling for invalid inputs and prompt errors.
  - [ ] Verify that the extracted count of questions/answers meets expectations.
- [ ] **Integration Testing**
  - [ ] Test the end-to-end flow: File retrieval → LLM processing → Storing extracted output.
  - [ ] Verify the structure and integrity of the new collections (`extracted-questions`, `extracted-answers`).
- [ ] **Student Data Model Testing (Design Review)**
  - [ ] Prepare conceptual test cases to validate relationships between student profiles and question attempts.
  - [ ] Plan for integration tests once the module is implemented.
- [ ] **Continuous Integration Setup**
  - [ ] Add the new tests to the CI pipeline.
  - [ ] Monitor CI results for regressions in the new features.

## 4. Documentation and Dagger Structure Updates
- [ ] **Dagger Structure Documentation**
  - [ ] Update `daggerStructure.md` to include:
    - `src/qaextractor/scripts/orchestration/llm_extraction.py`
    - `src/qaextractor/models/student_performance.py`
    - `src/qaextractor/tests/test_llm_extraction.py`
- [ ] **Final Review**
  - [ ] Ensure all documentation is updated and reviewed by the team.
  - [ ] Confirm the checklist items through peer review.
