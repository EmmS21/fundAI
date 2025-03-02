# AI Implementation – Next Steps

Now that our system is successfully writing exam papers (questions) and marking schemes (answers) into MongoDB, the next phase is to leverage an LLM to extract meaningful content from these files and to track student performance over time. The approach is as follows:

---

## 1. AI-Powered Content Extraction

### Objectives
- **Extract individual questions**: Automatically break down each exam paper into its constituent questions.
- **Extract supporting content**: For each question, extract any associated images, tables, sub-questions, and annotations.
- **Uniform processing for both questions and answers**: Apply a similar LLM-based approach for processing both exam papers and marking schemes.

### Requirements

#### File Processing Pipeline
- **Input**: 
  - Retrieve the PDF file from MongoDB using its FileID and FileName.
  - No special pre-processing (e.g., OCR or layout analysis) is required—simply send the PDF directly to the LLM.
- **LLM Integration**:
  - Send the entire PDF file along with a clear prompt to the LLM specifying exactly what needs to be extracted.
  - The prompt should instruct the LLM to:
    - Break the document into individual questions.
    - Extract any associated images, tables, and sub-questions.
    - Return a count of the number of questions found in the document.
- **Output**:
  - A structured JSON document that includes:
    - An array of individual questions and their detailed components.
    - A field for the total number of questions extracted.
  - This output should be stored in a new MongoDB collection (e.g., `extracted-questions` for exam papers and `extracted-answers` for marking schemes).

#### Validation & Quality Assurance
- Verify that the number of questions returned by the LLM matches expectations to prevent duplication or omission.
- Allow for manual review and correction in cases where the output is ambiguous or incomplete.

---

## 2. Processing Marking Schemes (Answer Sheets)

### Objectives
- **Extract detailed answer information**: Process marking scheme PDFs to extract annotations, scores, feedback, and score breakdowns.
- **Unified Approach**: Use the same LLM-based method—send the PDF along with a tailored prompt to extract the required answer details and a total count of answer items.

### Requirements
- **File Processing**:
  - Retrieve the marking scheme PDF from MongoDB.
  - Pass it to the LLM with a clear prompt describing the extraction tasks.
- **Output**:
  - A structured JSON document with the extracted answer details and an explicit count.
  - Store the output in the `extracted-answers` collection to enable correlation with the corresponding exam questions.

---

## 3. Student Performance Tracking

### Objectives
- **Record Student Interactions**: Track which questions a student has attempted and how they performed.
- **Maintain Historical Data**: Store performance data over time to analyze trends and progress.
- **Ensure Flexibility**: The system must be capable of handling real-time performance tracking as well as historical data for retrospective analysis.

### Requirements

#### Data Schema for Student Performance
- **Student Profile Collection**:
  - Unique student identifier (e.g., student ID).
  - Personal details (name, class, demographic information, etc.).
- **Question Attempts Collection**:
  - A document for each attempt at a question.
  - Link to the extracted question IDs from the `extracted-questions` collection.
  - Record metrics such as:
    - Timestamp of the attempt.
    - Score achieved and time taken.
    - Student answers and any accompanying feedback.
    - A flag to differentiate between initial attempts and subsequent reviews.
- **Historical Tracking**:
  - Incorporate time series data to monitor and analyze performance trends over multiple exam sessions.

---

## 4. Integration and Orchestration

### End-to-End Flow
1. **File Ingestion**:
   - Continue to write all original PDF files (both exam papers and marking schemes) into MongoDB.
2. **LLM-Based Extraction**:
   - Retrieve the PDF file from MongoDB.
   - Pass it to the LLM directly with a clear extraction prompt.
   - Store the resulting JSON (including the total question count) in the new collections (`extracted-questions` and `extracted-answers`).
3. **Student Interaction**:
   - Allow students to interact with the extracted questions via a dedicated portal.
   - Record each student's interaction and performance data in the student performance database.
4. **Analytics & Feedback Loop**:
   - Aggregate AI extraction data and student performance data.
   - Use these insights to make sure every question is accounted for and to improve the extraction process where necessary.

---

This approach ensures that every file is processed consistently using an LLM to directly extract all necessary details, with robust tracking of both the extraction quality and student performance over time.

---

## 5. Roadmap and Milestones

### Short-Term (Next 3 Months)
- Finalize AI extraction pipeline concept and select appropriate LLM models.
- Develop prototyping workflows for processing exam papers and marking schemes.
- Create new MongoDB collections for extracted data.
- Set up initial student performance schema and a pilot tracking system.

### Mid-Term (3 to 6 Months)
- Complete end-to-end integration between file ingestion, AI processing, and storage.
- Begin collecting and aggregating student performance data from live testing.
- Develop initial analytics dashboards and reporting tools.

### Long-Term (6 to 12 Months)
- Iterate on AI extraction quality using feedback loops.
- Expand student tracking to incorporate multiple exam sessions and comprehensive historical data.
- Roll out a full-featured adaptive learning platform and performance monitoring dashboard for educators.

---

## Conclusion

This next phase is pivotal for transforming raw exam data into actionable insights. By processing both exam papers and marking schemes with AI and combining this with detailed student performance tracking, we can create a robust platform that not only automates content extraction but also provides valuable analytics, personalized feedback, and long-term performance tracking. This approach will empower educators and students alike by offering real-time insights and a historical perspective on learning outcomes.