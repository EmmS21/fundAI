# Sync System Implementation Discussion

## Initial Requirements
We started by discussing the implementation of a sync system for an educational app with offline-first capabilities. The initial design included:

1. Priority Queue Tiers (T1-T4):
   - T1 (Highest): Final reports/scores
   - T2 (High): Paper cache updates
   - T3 (Medium): System metrics
   - T4 (Lowest): User profile changes

2. Differential Sync for Large Files:
   - Implement a way to sync only the changes in large files (like paper content)
   - Track file versions and calculate diffs

3. Batch Processing for Queued Interactions:
   - Group similar items together for more efficient syncing
   - Process items in batches rather than one by one

## Initial Implementation
We implemented a comprehensive sync system with:

1. QueueManager with priority-based processing
2. DifferentialSyncManager for efficient updates of large files
3. SyncService to coordinate the sync process
4. Enhanced FirebaseClient with batch operations

## Architectural Change
We then decided to change the architecture based on a new microservice approach:

- Instead of syncing full PDF past papers, we'll now sync individual questions extracted by a microservice
- These questions may include images and tables
- We need to track which questions we've fetched by paper and year
- This simplifies the sync mechanism as we no longer need complex differential sync

## Final Implementation
We updated the implementation to:

1. Remove differential sync components (DiffUtil and DifferentialSyncManager)
2. Enhance CacheManager to handle questions with their associated assets
3. Update SyncService to handle question syncing instead of paper syncing
4. Maintain the priority queue system with updated priorities
5. Keep batch processing for efficiency

The new system provides several benefits:
- More granular syncing of content
- Reduced bandwidth usage
- Better offline experience
- Improved content management
- Simplified architecture

We ensured the system tracks paper year and number for each question, which is essential for organizing the content properly.

## Database Schema
- cached_questions: Stores individual questions with references to their paper
- question_assets: Stores images, tables, and other media associated with questions
- paper_metadata: Tracks which papers we have and how many questions are cached

## Technical Details
The implementation includes:
- Priority-based queue processing
- Batch operations for related items
- Improved serialization for complex data types
- Persistent queue storage across app restarts
- Thread-safe operations for concurrent access
- Error handling with retry logic
- Network status awareness

This approach provides a more efficient way to manage exam content while maintaining the offline-first philosophy of the application.
