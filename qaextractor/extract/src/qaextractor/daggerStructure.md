# Dagger Module Structure

## Directory Structure
├── .env                      # Environment variables (not in git)
├── .gitignore                # Git ignore file
├── src/
│   └── qaextractor/
│       ├── main.py           # Main Dagger module with function definitions
│       ├── scripts/          # External scripts for container execution
│       │   ├── orchestration/  # Orchestration scripts
│       │   │   ├── process_level.py    # Process a single education 
│       │   │   ├── extraction_pipeline.py  # NEW: Orchestrates the extraction 
│       │   │   ├── constants.py            # Update with new constants
│       │   │   ├── create_document.py  # Create MongoDB document
│       │   │   ├── llm_extraction.py       # EXISTING: May need minor updates
│       │   │   ├── pdf_extractor.py         # EXISTING: May need minor updates
│       │   │   └── image_processor.py
│       ├── models/           # Data model definitions
│       │   ├── extracted_question.py       # NEW: Data model for extracted 
│       │   └── student_performance.py  # Student performance data models
│       └── tests/            # Test files
│           ├── test_drive.py         # Tests for Drive functionality
│           ├── test_mongodb.py       # Tests for MongoDB functionality
│           ├── test_orchestration.py # Tests for orchestration
│           └── test_extraction_pipeline.py # NEW: Tests for extraction pipeline