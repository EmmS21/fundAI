# Caching Logic Update - Paused

**Goal:** Implement a more efficient cache update mechanism that only fetches new questions when needed, based on user completion of existing cached content.

**Problem:**
- The current `CacheManager` uses a high-frequency timer, causing repeated, unnecessary checks for updates even when the local cache (`cached_questions`) has sufficient data. This is inefficient and wastes resources.

**Proposed Solution:**
- Replace the timer-based trigger with an event-driven one (app start, network becomes online).
- Implement a "completion-based" check: Only initiate a fetch for a specific subject/level if the user has completed a certain percentage (e.g., 75%) of the questions from the *most recent year* already cached for that subject/level.

**Progress:**
1.  **Database Schema Updated:** Added a `cached_question_id` column (nullable TEXT with Foreign Key to `cached_questions.question_id`) to the `question_responses` table/model (`src/data/database/models.py`). This column is essential to link a user's response back to the specific cached question they answered. (Alembic migration or manual `ALTER TABLE` was required).

**Next Steps (Paused):**
2.  **Populate `cached_question_id`:** Modify the application code where user answers are saved to the `question_responses` table. Ensure that when a `QuestionResponse` is created for an answer to a cached question, the `cached_question_id` field is correctly populated with the ID of the corresponding `CachedQuestion`.
3.  **Implement Cache Check Logic:** Modify `CacheManager` to:
    - Remove the high-frequency timer.
    - Add a method `_should_update_subject(subject_info)` that queries `question_responses` (using the `cached_question_id`) to calculate the completion percentage for the latest cached year and returns `True` if the threshold is met.
    - Add a method `trigger_update_check()` that is called by external events (app start, network online) and uses `_should_update_subject` to decide whether to initiate an update for specific subjects.
4.  **Connect Triggers:** Connect `NetworkMonitor.status_changed` (online signal) and app startup logic to call `CacheManager.trigger_update_check()`.

**Reason for Pausing:**
- Step 2 requires the UI logic for displaying questions (from `cached_questions`) and capturing/saving user answers (creating `QuestionResponse` entries) to be implemented first. We need this UI interaction flow to exist before we can modify it to save the `cached_question_id`.

---
