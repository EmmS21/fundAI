# Development Checklist

## Backend Engineer

### Data Model Extensions
- [x] Extend `ExamResult` model
  - Add `report_version` field (preliminary/final)
  - Add `last_ai_sync` timestamp
  - Create migration script for existing records
- [ ] Implement `PaperCache` model
  - Subject/level/year relationships (link to `UserSubject`)
  - Binary storage field for paper content
  - Completion status tracking per year
- [ ] Build cache invalidation system
  - 5-year rotation logic
  - Completion-based refresh triggers
  - Cryptographic shredding for rotated data

### Sync System
- [ ] Enhance `SyncService`
  - Implement priority queue tiers (T1-T4)
  - Add differential sync for large files
  - Create batch processing for queued interactions
- [ ] Develop security features
  - AES-256 encryption for local cache
  - Hardware-bound key integration with `HardwareIdentifier`
  - Automatic backup triggers on sync events

### Performance Tracking
- [ ] Create `SubjectProgress` model
  - Historical accuracy rate calculations
  - Time-per-topic metrics
  - Peer benchmark comparison system
- [ ] Enhance `QuestionResponse`
  - Add `is_preliminary` flag
  - Version history storage for AI feedback
  - Topic tagging relationships

## ML/AI Engineer

### AI Core System
- [ ] Implement `AIManager` class
  - Model switching logic (local/Groq)
  - Automatic fallback mechanisms
  - Request batching system
- [ ] Develop feedback pipelines
  - Preliminary report generation (offline)
  - Final report generation (online)
  - Version diff tracking system

### Model Operations
- [ ] Local GGUF integration
  - .cpp model loader implementation
  - Versioned model storage in `src/core/ai_models/`
  - Diff-based update system
- [ ] Groq API adapter
  - Batch request handling
  - Rate limiting implementation
  - Error fallback to local model

### Analytics
- [ ] Build topic tagging system
  - Question-to-topic mapping
  - Accuracy tracking per topic
  - Weakness identification algorithm
- [ ] Implement monitoring
  - Model performance metrics
  - Cache effectiveness tracking
  - Offline success rate analytics

## Frontend Engineer

### Exam Interaction
- [ ] Implement subject test buttons
  - Add "Take Test" button per subject card
  - Dynamic button state based on selected levels
  - Test availability indicators (ready/upcoming)
  - Level selection popup with:
    - Radio buttons for selected levels
    - Estimated time per level
    - Recent performance preview

### Status System
- [ ] Add UI indicators
  - Sync status badges (preliminary/final)
  - **New:** Report readiness badges
    - Preliminary (orange) - local AI complete
    - Final (green) - cloud sync verified
  - Cache freshness display in `ProfileInfoWidget`
  - Offline mode warning system

### Report Interface
- [ ] Develop version comparison UI
  - Side-by-side preliminary/final diff
  - Color-coded change indicators
  - Historical accuracy timelines
  - **New:** Report status integration
    - Badge system in `SubjectCard`
    - Click-to-expand version history

### Profile Integration
- [ ] Add test launch workflow
  - Subject card button states:
    - Active (tests available)
    - Disabled (no cached papers)
    - Loading (generating/pending)
  - Visual feedback during paper generation
  - Error states for missing requirements

## Cross-Team Dependencies
1. **Backend → ML**: Coordinate on `AIManager` API surface
2. **ML → Frontend**: Define report format spec for UI rendering
3. **Frontend → Backend**: Agree on cache status API endpoints
4. **All Teams**: Sync on encryption/decryption flow UX
5. **Backend → Frontend**: Provide network quality metrics API
6. **Frontend → Backend**: 
   - Require test availability API endpoint
   - Get report status flags from `ExamResult`
7. **ML → Frontend**:
   - Provide test generation progress events
   - Share report formatting specifications
