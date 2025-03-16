# Answer Extraction Pipeline Implementation Checklist

This checklist outlines the steps needed to implement the answer extraction pipeline, focusing on an incremental development approach and code reuse where possible.

## Phase 1: Find Matching Answer Documents

- [x] Create `find_matching_answers.py` script in `extract/src/qaextractor/scripts/orchestration/`
  - [x] Adapt code from `find_unprocessed.py` to query `pp-answers` collection
  - [x] Implement cross-reference logic to match answers with processed questions
  - [x] Test script by directly executing it to verify it returns unprocessed answer documents with matching question documents
  - [x] Verify that the matching logic correctly compares level, subject, year, paper, and term

## Phase 2: Develop Answer Extraction Components

- [x] Create `insert_answers.py` script
  - [x] Adapt from `insert_questions.py` 
  - [x] Modify to store data in `extracted-answers` collection
  - [x] Update document structure for answers (include matching_question_id)
  - [x] Add reference to the original question document
  - [ ] Test script independently to ensure it properly stores answer data

- [x] Generalize existing `mark_processed.py` script
  - [x] Modify to support both `pp-questions` and `pp-answers` collections
  - [x] Add parameter to specify which collection to update
  - [x] Ensure metadata includes references to matched questions/answers
  - [x] Add proper argument parsing for command-line usage
  - [ ] Test script independently to verify it properly marks answer documents as processed

## Phase 3: Implement Single Answer Extraction 

- [x] Create the answer extraction LLM prompt
  - [x] Define prompt structure based on the one in nextsteps.md
  - [x] Create JSON schema for answers with fields for question numbers, answer text, marks, alternatives, etc.
  - [x] Ensure prompt instructs LLM to maintain original question numbering

- [x] Create `single_answer` function in `Qaextractor` class (or adapt `single` function)
  - [x] Reuse PDF download and extraction code from `single` function
  - [x] Implement the answer-specific LLM prompt
  - [x] Ensure proper parsing of LLM output into JSON
  - [x] Test with a single answer document to verify extraction works correctly

## Phase 4: Implement Answer Pipeline Function

- [ ] Add `extract_answers` function to `Qaextractor` class in `main.py`
  - [ ] Adapt code from the existing `run` function
  - [ ] Use `find_matching_answers.py` instead of `find_unprocessed.py`
  - [ ] Process each answer document that has a matching processed question document
  - [ ] Use `insert_answers.py` to store extracted answers
  - [ ] Use generalized `mark_processed.py` to mark processed answer documents
  - [ ] Include proper error handling and reporting
  - [ ] Add batch processing with skip/limit parameters

## Phase 5: Testing and Validation

- [x] Test finding matching answer documents
  - [x] Verify we can find all unprocessed answer documents with matching questions
  - [x] Confirm cross-reference logic works correctly

- [ ] Test single answer extraction
  - [ ] Process a single answer document
  - [ ] Verify the LLM prompt produces correctly structured output
  - [ ] Check that answer extraction captures marking criteria, alternative answers, etc.

- [ ] Test full pipeline
  - [ ] Run the complete `extract_answers` function
  - [ ] Process a batch of answer documents
  - [ ] Verify end-to-end functionality

## Phase 6: Integration and Optimization

- [ ] Improve error handling and logging
  - [ ] Add specific error messages for answer extraction failures
  - [ ] Implement retry logic for intermittent failures
  - [ ] Ensure meaningful error reporting

- [x] Optimize code reuse
  - [x] Identify common functionality between question and answer extraction
  - [x] Refactor shared code into utility functions (generalized `mark_processed.py`)
  - [x] Ensure consistent patterns across both extraction pipelines

- [ ] Document the implementation
  - [ ] Update function documentation with clear descriptions
  - [ ] Document database schema for `extracted-answers` collection
  - [ ] Add usage examples and command-line instructions
