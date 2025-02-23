# Exam Assistant Project Scope

## Context
We're building an offline-first educational application that provides mock exam generation, performance tracking, and AI-powered feedback. The system leverages both local AI models (offline) and cloud-based Groq API (online) to deliver immediate preliminary feedback and comprehensive final reports. The application maintains a 5-year rolling cache of past papers and student interactions, with intelligent sync capabilities when connectivity is restored.

## Core Requirements

### Offline-First Architecture
1. **Local AI Integration**  
   - Embed a quantized .cpp AI model (GGUF format) for immediate feedback generation when offline  
   - Model files stored in `src/core/ai_models/` with versioning  
   - Automatic model updates when online (diff-based patching)

2. **Caching System**  
   - Maintain 5-year rolling cache of past papers per subject/level combination  
   - Smart cache invalidation: Only fetch new papers when all questions from oldest cached year are completed  
   - Cache storage in SQLite using existing models (reference: `models.py` lines 15-123)  
   - Cache metadata tracking (last accessed, completion status)

3. **Sync Service Enhancements**  
   - Extend existing `SyncService` (lines 21-185) to handle:  
     - AI report versioning (preliminary vs final)  
     - Batch processing of queued offline interactions  
     - Differential sync for large past paper files  
   - Priority queueing system for critical sync operations

### AI Integration Layer
1. **Unified AI Interface**  
   - `AIManager` class handling model switching:  
     - Local model for immediate offline responses  
     - Groq API for final reports when online  
   - Automatic fallback mechanisms with user notification  
   - Request batching for efficiency

2. **Feedback Pipeline**  
   - Two-stage marking system:  
     1. PreliminaryReport (offline): Basic scoring and quick feedback  
     2. FinalReport (online): Detailed analysis and suggestions  
   - Report version tracking in `ExamResult` model (extend lines 51-70)

### Data Model Extensions
1. **Assessment Tracking**  
   - New `PaperCache` model:  
     - Subject/level mapping (link to `UserSubject` lines 95-113)  
     - Year tracking  
     - Completion status  
     - Binary storage for paper content  
   - Enhanced `QuestionResponse` (lines 71-93):  
     - Add `is_preliminary` flag  
     - Version history for AI feedback  
     - Topic tagging system

2. **Performance Analytics**  
   - New `SubjectProgress` model tracking:  
     - Historical accuracy rates  
     - Time-per-topic metrics  
     - Comparative analysis against peer benchmarks  
   - Integration with existing `medals` system (reference: `User` model line 31)

### Security & Reliability
1. **Offline Data Protection**  
   - AES-256 encryption for local cache  
   - Hardware-bound encryption keys using existing `HardwareIdentifier`  
   - Automatic backup system tied to sync events

2. **Connection Management**  
   - Enhanced `NetworkMonitor` (lines 14-94) with:  
     - Predictive connectivity scoring  
     - Bandwidth-aware sync throttling  
     - Emergency cache preservation modes

### User Experience
1. **Status System**  
   - Visual indicators for:  
     - Preliminary vs final reports  
     - Cache freshness status  
     - Offline mode limitations  
   - Sync progress integration into existing profile UI (extend `ProfileInfoWidget` lines 600-675)

2. **Smart Prefetching**  
   - Usage-pattern analysis for:  
     - Anticipatory paper downloads  
     - Background model warmup  
     - Frequently-needed resource caching

## Workflow Integration

### Exam Lifecycle
1. Paper Generation:  
   - Check cache for available papers  
   - Generate from local template if offline  
   - Fetch latest from server if online

2. Answer Capture:  
   - Store responses in `QuestionResponse` with offline flag  
   - Immediate preliminary analysis via local AI

3. Feedback Delivery:  
   - Queue preliminary report for sync  
   - Batch process final reports when connected  
   - Maintain version association in UI

### Sync Architecture
1. Priority Tiers:  
   - Tier 1: User profile data (existing sync)  
   - Tier 2: Final reports and scores  
   - Tier 3: Paper cache updates  
   - Tier 4: System metrics

2. Conflict Resolution:  
   - Timestamp-based merging for scores  
   - User-prompted resolution for significant discrepancies  
   - Version rollback capabilities

## Compliance Requirements
1. **Data Retention**  
   - 5-year cache rotation with cryptographic shredding  
   - GDPR-compliant sync pruning

2. **Accessibility**  
   - Offline-first UI patterns  
   - Bandwidth-sensitive asset loading  
   - Progressive enhancement for online features

## Monitoring
1. **Health Tracking**  
   - Model performance metrics  
   - Cache hit/miss ratios  
   - Offline success rates

2. **Alert System**  
   - Threshold-based notifications for:  
     - Extended offline periods  
     - Cache depletion risks  
     - Model accuracy drift
