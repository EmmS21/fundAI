# Past Paper Processing AI Agent

## Overview
A Dagger-powered AI agent that processes PDF past exam papers from various exam boards, extracting questions, answers, marking schemes, and associated metadata. The agent operates as a pipeline of containerized modules, ensuring deterministic processing and reliable output formats. All processed content is stored in a NoSQL database, making it available for educational applications through a simple API.

## Key Features

### PDF Processing Pipeline
- Ingests PDF past papers and their corresponding answer sheets
- Uses OCR and structure recognition to parse content accurately
- Extracts text, tables, mathematical notation, and images
- Preserves formatting and relationships between content elements

### Content Extraction
- Identifies individual questions and sub-questions
- Extracts marking schemes and model answers
- Maintains question metadata (year, paper number, topic, etc.)
- Processes mathematical notation and specialized formatting

### Intelligent Analysis
- Rates question difficulty based on marking scheme complexity
- Classifies questions by topic and subtopic
- Identifies areas where students historically struggle
- Creates relationships between similar questions across years

### Modular Architecture
- Built as containerized Dagger modules with clear interfaces
- Each processing step runs in isolated, reproducible environments
- Deterministic execution through validation checks and retries
- Comprehensive tracing of every step in the pipeline

### Database Integration
- Stores processed content in MongoDB
- Tracks processing status of all papers
- Maintains versioning for content updates
- Provides efficient query capabilities across all metadata

## Technical Advantages

### Deterministic Processing
- Each module includes output validation checks
- Failed validations trigger automatic retries with adjusted parameters
- Processing history tracked for debugging and improvement

### Scalability
- Horizontally scalable through containerized architecture
- Parallel processing of multiple papers
- Efficient caching of intermediate results

### Deployment Flexibility
- Designed for deployment on Modal
- Runs anywhere with container support
- No vendor lock-in

### Developer Experience
- Clear module interfaces
- Extensive logging and tracing
- Easy local testing and debugging

## Use Cases
- Creating question banks for study applications
- Building spaced repetition systems based on question difficulty
- Generating practice tests with specific topic focus
- Analyzing question patterns across years
