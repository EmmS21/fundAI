# Past Paper Processor - Project Structure

## Directory Structure
past-paper-processor/
├── dagger/                          # Dagger module definitions
│   ├── src/
│   │   └── paper_processor/
│   │       ├── __init__.py
│   │       ├── main.py             # Main Dagger module
│   │       ├── pdf.py             # PDF processing functions
│   │       ├── answer.py          # Answer processing functions
│   │       ├── analysis.py        # Analysis functions
│   │       └── storage.py         # Database operations
│   ├── pyproject.toml             # Python project configuration
│   └── dagger.json                # Dagger module configuration
├── api/
│   ├── main.py                    # FastAPI application entry
│   ├── routes/
│   │   ├── papers.py             # Paper processing endpoints
│   │   └── questions.py          # Question retrieval endpoints
│   └── models/
│       ├── paper.py              # Paper data models
│       ├── question.py           # Question data models
│       └── answer.py             # Answer data models
├── tests/
│   ├── test_papers/             # Sample papers for testing
│   └── test_answers/            # Sample answers for testing
├── modal.py                      # Modal deployment configuration
└── config.yaml                   # Configuration settings

## Module Pipeline Flow

1. PDF Processing:
   - Input: PDF file
   - Steps: ingestion -> ocr -> extractor
   - Output: Structured question data

2. Answer Processing:
   - Input: Answer PDF + Question data
   - Steps: matching -> marking
   - Output: Enhanced question data with answers

3. Analysis:
   - Input: Question data with answers
   - Steps: difficulty -> topic
   - Output: Fully analyzed question data

4. Storage:
   - Input: Analyzed question data
   - Steps: mongodb storage
   - Output: Database confirmation

Each module includes:
- Input validation
- Core processing
- Output validation
- Retry mechanism for non-deterministic AI operations