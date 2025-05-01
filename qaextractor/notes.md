# Presentation Talking Points: Dagger AI Agent for Q&A Extraction

## Overall Goal
*   Develop an AI Agent using Dagger to automate the extraction of questions, answers, and related metadata from educational documents (like exam papers and marking schemes).
*   The extracted data is structured for use in an AI Tutor system.

## Dagger Pipeline: Single Document Processing (`main.py`)

This pipeline focuses on processing individual PDF documents (or pairs of question/answer PDFs) to extract structured Q&A data.

### 1. PDF Ingestion & Preprocessing
*   **Input:** Takes a PDF file (e.g., an exam paper or marking scheme) as input.
*   **Process:**
    *   Identifies the type of document (e.g., question paper vs. answer key).
    *   Utilizes specialized Python scripts (`pdf_extractor.py`, `answer_pdf_extractor.py`) executed within Dagger containers.
    *   These scripts leverage libraries like `PyPDF2` for text extraction and `pdf2image`, `Pillow`, `OpenCV` for image handling.
*   **Output:** Extracted raw text content and identified image data (including potential URLs or references) from the PDF.

### 2. Image Identification and Handling
*   **Rationale (as observed in code):** The initial PDF processing step seems crucial for identifying not just text but also the presence and location of images *within* the document structure. Text extraction includes special markers (`[IMAGE for QX: ...]`, `[COVER IMAGE: ...]`) that reference images.
*   **Process:**
    *   The `pdf_extractor.py` script likely uses libraries like `pdf2image` and potentially OCR or layout analysis (using OpenCV/Numpy) to identify image blocks and associate them with page numbers or question numbers.
    *   The extracted text retains markers pointing to these images.
    *   The LLM is later instructed (see next step) on how to use these markers and the extracted image data (like URLs stored during PDF processing) to link images correctly to questions.
*   **Output:** Text content with image markers, and a separate collection of image data (like URLs, dimensions, page numbers).

### 3. LLM-Powered Q&A Extraction
*   **Input:** The extracted text (with image markers) and image data from the previous step.
*   **Process:**
    *   Uses a Large Language Model (LLM) via a dedicated script (`llm_extraction.py`), likely interacting with an API like Gemini/OpenAI.
    *   Employs distinct, carefully crafted prompts depending on whether questions or answers are being extracted.
    *   Prompts instruct the LLM to:
        *   Identify individual questions/answers.
        *   Extract full text, context materials (like passages), question numbers, marks.
        *   Associate images with questions using the markers and provided image data (mapping markers to URLs).
        *   Estimate difficulty, cognitive level, and steps required.
        *   Distinguish between textual context and visual elements (charts, graphs labelled as 'Text C' should be marked as images).
        *   Output the results in a structured JSON format.
*   **Output:** Structured JSON containing detailed information for each question or answer, including text, context, marks, associated images (with URLs), and AI-generated metadata (difficulty, etc.).

### 4. Metadata Enrichment
*   **Input:** The structured JSON from the LLM and the original file path/name.
*   **Process:**
    *   Parses the file path or name to extract contextual metadata like educational level (e.g., GCSE, A-Level), subject, and year.
    *   Uses predefined constants and mapping logic (potentially from `constants.py` via `constants_module`) to standardize this information.
*   **Output:** The structured JSON augmented with standardized metadata (level, subject, year).

### 5. Final Output Generation
*   **Input:** Enriched JSON data.
*   **Process:**
    *   Consolidates all extracted and generated information.
    *   Formats the final result, potentially adding pipeline metadata (e.g., total questions/answers extracted).
    *   The `extracted_question.py` likely defines the final data structure/object model.
*   **Output:** A final JSON string representing the successfully processed document, ready for ingestion into the AI Tutor's database or further processing.

## Areas for Further Discussion (Based on User Query)

*   **Document Discovery Pipeline:** (Details needed) Discuss the separate Dagger pipeline responsible for finding and queuing the PDF documents for processing by the extraction pipeline described above. What sources does it scan? How does it manage state?
*   **AI-Powered Question Grouping:** (Details needed) Explain how AI is used *after* extraction to group related questions. Is this based on topic modeling, semantic similarity, curriculum linkage? Does this happen in a separate Dagger module? What are the goals of this grouping (e.g., identifying prerequisite knowledge, creating topic-based quizzes)?
*   **Rationale for Image-First Approach (Refined):** Elaborate on *why* identifying images early in the PDF processing stage (before the main LLM extraction) was chosen. Was it to improve the LLM's ability to link images correctly? To handle complex layouts where images interrupt text flow? Was it an iterative discovery during development?
