# New Database Design for Questions, Answers, and Student Progress

Below is a proposed design for the new NoSQL databases to support our system. We assume the processed exam paper and marking scheme PDFs have already been stored. This design uses reference keys (e.g., exam IDs or FileIDs) to correlate data across databases.

---

## 1. Extracted Questions Database

This collection stores each exam paper's extracted questions. Since individual papers can have 50 to 100+ questions, we encapsulate the questions in an array within a document that references the original exam paper.

### Document Structure

- **_id**: Auto-generated document ID.
- **exam_id**: A unique key referencing the original exam paper (e.g., FileID from MongoDB).
- **paper_reference**: An object containing meta-information about the paper:
  - **Level**: Education level (e.g., ASLevel, OLevel, Primary).
  - **Subject**: Subject name.
  - **Year**: Year associated with the exam.
  - **FileName**: Original filename.
- **questions**: An array where each element represents a single question.
  - **question_id**: A unique identifier (could be generated sequentially per paper).
  - **text**: Full question text.
  - **images**: An array of references or URLs for any associated images.
  - **tables**: An array of table data objects.
  - **sub_questions**: An array for any sub-question breakdowns.
  - **metadata**: Additional attributes (e.g., difficulty, estimated marks).
- **total_questions**: The total number of questions extracted.
- **extraction_date**: Timestamp indicating when the extraction occurred.

---

## 2. Extracted Answers Database

This collection stores detailed answer information extracted from marking schemes. The structure parallels the questions database so that answers can be correlated with their corresponding questions.

### Document Structure

- **_id**: Auto-generated document ID.
- **exam_id**: A unique key referencing the related exam or marking scheme PDF.
- **paper_reference**: An object with metadata similar to the questions database:
  - **Level**: Education level.
  - **Subject**: Subject name.
  - **Year**: Exam year.
  - **FileName**: Original filename.
- **answers**: An array holding each extracted answer or marking item.
  - **answer_id**: A unique identifier for the answer.
  - **text**: Extracted answer text.
  - **annotations**: Any comments, marks, or feedback associated with the answers.
  - **scores**: If applicable, a breakdown of scores.
  - **metadata**: Additional contextual information.
- **total_answers**: The total number of answer items extracted.
- **extraction_date**: Timestamp for when the extraction process was completed.

---

## 3. Student Performance Tracking Database

To track student interactions and performance, we can utilize two interrelated collections: one for student profiles and a separate one for individual question attempts. A reference key (e.g., student ID and exam_id) will be critical for linking progress data to the original questions.

### A. Student Profiles Collection

### Document Structure

- **_id**: Auto-generated student profile ID.
- **student_id**: A unique student identifier.
- **name**: Student's full name.
- **class**: Class or grade information.
- **demographics**: Optional additional details (e.g., age, gender).
- **created_date**: Timestamp when the profile was created.

### B. Question Attempts Collection

This collection stores each attempt at answering individual questions. Each document corresponds to a single question attempt.

### Document Structure

- **_id**: Auto-generated document ID.
- **student_id**: Reference key linking to the Student Profiles collection.
- **exam_id**: Reference key indicating which exam paper (or extracted questions document) the attempt relates to.
- **question_id**: Identifier or key matching the specific question in the extracted questions document.
- **attempt_data**:
  - **answer_given**: The student's submitted answer.
  - **is_correct**: Boolean flag (if applicable) based on comparison with the marking scheme.
  - **score_awarded**: Marks or score obtained for this attempt.
  - **time_taken**: Duration for answering the question.
- **timestamp**: When the attempt was recorded.
- **attempt_type**: Flag to indicate if this is an initial attempt or a review.

---

## Key Considerations

- **Reference Keys**: Use the unique exam_id (or FileID) as a linking field across the extracted questions, answers, and student progress databases.
- **Scalability**: The design anticipates multiple exam sessions and large volumes of embedded questions or answers per exam. Indexing on reference keys (e.g., exam_id, student_id, question_id) will ensure efficient queries.
- **Flexibility**: The schemas are designed to allow additional metadata or fields to be added as needed without disrupting existing references.

This design forms the backbone for a flexible and scalable solution to track detailed exam content and student performance over time.
