# Past Paper Processing Microservice

## Overview
A dedicated microservice that processes PDF past papers from various exam boards, extracts questions and answers, and makes them available to the Exam Assistant application through a simple API. This service handles the entire content pipeline from raw PDFs to structured, queryable exam content.

## Core Responsibilities
1. **PDF Ingestion & Processing**
   - Accept PDF uploads from authorized sources
   - Parse PDFs using OCR and structure recognition
   - Extract images, diagrams, and formatted content
   - Match questions with corresponding marking schemes

2. **Content Extraction**
   - Identify individual questions and sub-questions
   - Extract marking schemes and model answers
   - Preserve mathematical notation and special formatting
   - Maintain question metadata (year, paper number, marks, etc.)

3. **Topic Classification**
   - Automatically tag questions with subject topics
   - Determine difficulty level through heuristic analysis
   - Create relationships between similar questions
   - Build topic taxonomy for navigation/filtering

4. **Storage & Indexing**
   - Store processed questions in NoSQL database (MongoDB)
   - Index for efficient topic/difficulty/year queries
   - Maintain versioning for updated marking schemes
   - Track usage statistics per question

5. **API Service**
   - Provide RESTful endpoints for question retrieval
   - Support batched downloads for offline caching
   - Implement query filters (subject, level, year, topic)
   - Authenticate main application requests

## Technical Architecture

### Components
1. **Ingestion Worker**
   - Processes uploaded PDFs in queue
   - Runs OCR with specialized academic content models
   - Splits papers into questions with metadata

2. **Question Processor**
   - Structures extracted text into question format
   - Identifies question parts and subparts
   - Extracts diagrams and mathematical expressions
   - Matches questions to marking scheme

3. **Topic Classifier**
   - Uses NLP to identify subject topics
   - Applies taxonomical classification
   - Generates semantic embeddings for similarity

4. **API Gateway**
   - Handles authentication and throttling
   - Routes requests to appropriate services
   - Manages caching for popular content

5. **Admin Dashboard**
   - Content management interface
   - Manual verification workflow
   - Usage analytics and reporting

### Data Storage
1. **MongoDB** (primary storage)
   - Questions collection (with embedded parts)
   - Marking schemes collection
   - Topic taxonomy collection
   - Usage statistics collection

2. **Redis** (caching layer)
   - Frequently accessed questions
   - Topic navigation structures
   - Authentication tokens

3. **MinIO/S3** (binary storage)
   - Original PDF files
   - Extracted images and diagrams
   - Rendered equation images

## Integration Points

### For Exam Assistant Application
1. **Content API**
   - `GET /api/v1/papers?subject={subject}&level={level}&year={year}`
   - `GET /api/v1/questions?topic={topic}&difficulty={difficulty}`
   - `GET /api/v1/questions/random?count={count}&subject={subject}`
   - `GET /api/v1/questions/{id}/marking-scheme`

2. **Batch Operations**
   - `GET /api/v1/batch/papers?years=[2019,2020,2021]&subject={subject}`
   - `GET /api/v1/updates?since={timestamp}&subject={subject}`

3. **Webhooks**
   - Content update notifications
   - New paper availability alerts

### Authentication
- API key-based authentication
- JWT tokens for session management
- Rate limiting per client application

## Deployment Model
- Containerized microservices (Docker)
- Kubernetes orchestration
- Horizontal scaling for processing workers
- CDN integration for static assets (diagrams, images)

## Monitoring & Operations
- Processing queue metrics
- Content coverage analytics
- Error rate tracking
- Processing time measurements

## Data Pipeline Workflow
1. **Content Acquisition**
   - Exam board partnership agreements
   - Scheduled PDF harvesting from authorized sources
   - Manual upload interface for administrators

2. **Processing Pipeline**
   - PDF → OCR → Question Extraction → Topic Classification → Storage
   - Parallel processing of multiple papers
   - Quality verification for high-confidence questions

3. **Content Updates**
   - Version tracking for amended marking schemes
   - Notifications for client applications
   - Differential updates to minimize bandwidth

## Security & Compliance
- Copyright compliance with exam boards
- Secure storage of proprietary content
- Access controls based on licensing agreements
- Audit trails for content access

## Scalability Considerations
- Support for multiple exam boards and countries
- Processing pipeline scalable to thousands of papers
- Content API designed for high-volume concurrent access
- Efficient caching to reduce database load
