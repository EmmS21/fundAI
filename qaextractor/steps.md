# Implementation Checklist

## Phase 1: Basic Google Drive Access & Structure Analysis
- [x] Set up service account authentication
- [x] Create basic function to list files from a specific folder
- [x] Create function to identify education level (ASLevel, OLevel, Primary)
- [x] Map out folder structure for each level:
  - ASLevel: Level → Subjects → (Exams|MS) → Years → Papers
  - OLevel: Level → Subjects → (Exams|MS) → Years → Papers
  - Primary: Level → Subjects → Years → (PP|MS) → Papers

  - ASLevel: Level → Subjects → Marking Schema → Years → Papers
  - OLevel: Level → Subjects → Marking Schema → Years → Papers
  - Primary: Level → Subjects → Years → MS → Papers


## Phase 2: Paper Name Parser
- [x] Create paper name parser function that extracts:
  - Paper number (required)
  - Term (default to "January" if not specified)
  - Version (optional)
- [x] Handle different paper name formats:
  ```
  - Paper-1.pdf → {paper: 1, term: "January"}
  - Paper-2Oct.pdf → {paper: 2, term: "October"}
  - InsertPaper-2Oct.pdf → {paper: 2, term: "October"}
  - Paper-4:42.pdf → {paper: 4, term: "January", version: 42}
  - Paper-3:31Oct.pdf → {paper: 3, term: "October", version: 31}
  ```

## Phase 3: Path Tracking
- [ ] Add path array to existing structure:
  ```python
  ["ASLevel", "Mathematics", "Exams", "2023", "Paper-1.pdf"]
  ```
- [ ] Ensure path matches MongoDB FolderStructure field requirements

## Phase 4: MongoDB Integration
- [x] Create separate function for MongoDB connection
- [x] Design flexible document structure for pp-questions collection:
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
- [x] Add error handling for MongoDB operations

## Phase 5: Integration and Orchestration
- [ ] Create main orchestrator function that:
  - Identifies education level
  - Selects appropriate navigation pattern
  - Processes folders according to pattern
  - Parses paper names
  - Creates MongoDB documents
  - Maintains state during processing
- [ ] Add checkpoint system for recovery
- [ ] Add logging for each level of navigation
- [ ] Create progress tracking across levels

## Phase 6: Testing and Validation
- [ ] Test paper name parsing:
  - All known formats
  - Edge cases
  - Invalid formats
- [ ] Test individual level processing:
  - ASLevel complete path
  - OLevel complete path
  - Primary complete path
- [ ] Test error scenarios:
  - Missing folders
  - Incorrect structure
  - Network issues
  - Invalid paper names
- [ ] Verify MongoDB entries for each level
- [ ] Add structure validation for each level

## Phase 7: Optimization and Monitoring
- [ ] Add batch processing for MongoDB insertions
- [ ] Add progress reporting per:
  - Education level
  - Subject
  - Year
  - Paper format type
- [ ] Add execution time tracking
- [ ] Create monitoring dashboard for:
  - Processing status
  - Error rates
  - Paper format distribution
  - Completion rates
- [ ] Add configuration file for:
  - Folder IDs
  - Structure patterns
  - MongoDB settings
  - Valid paper name patterns

## Phase 8: Documentation and Maintenance
- [ ] Document folder structure variations
- [ ] Document paper naming conventions
- [ ] Create recovery procedures
- [ ] Add system health checks
- [ ] Create maintenance scripts
- [ ] Document all configuration options
