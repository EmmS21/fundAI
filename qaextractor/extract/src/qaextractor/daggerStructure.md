# Dagger Module Structure

## Directory Structure
├── .env                      # Environment variables (not in git)
├── .gitignore                # Git ignore file
├── src/
│   └── qaextractor/
│       ├── main.py           # Main Dagger module with function definitions
│       ├── scripts/          # External scripts for container execution
│       │   ├── drive/        # Google Drive related scripts
│       │   │   ├── list_levels.py      # Script to list education levels
│       │   │   ├── map_structure.py    # Script to map folder structure
│       │   │   └── paper_parser.py     # Script for parsing paper names
│       │   ├── mongodb/      # MongoDB related scripts
│       │   │   ├── connect.py          # MongoDB connection script
│       │   │   └── document.py         # Document structure definitions
│       │   └── orchestration/  # Orchestration scripts
│       │       ├── process_level.py    # Process a single education level
│       │       ├── constants.py        # Constants for the module
│       │       ├── create_document.py  # Create MongoDB document
│       │       └── llm_extraction.py   # **NEW:** LLM extraction module for AI processing
│       ├── models/           # **NEW:** Data model definitions
│       │   └── student_performance.py  # **NEW:** Student performance data models
│       └── tests/            # Test files
│           ├── test_drive.py         # Tests for Drive functionality
│           ├── test_mongodb.py       # Tests for MongoDB functionality
│           ├── test_orchestration.py # Tests for orchestration
│           └── test_llm_extraction.py  # **NEW:** Tests for LLM extraction module