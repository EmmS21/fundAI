# Full Report Generation & Notification Implementation Plan

This plan outlines the steps to fully implement the generation of full reports via Groq and notify the user of new, unread reports.

## Task 1: Implement "Viewed" Status Tracking in `answer_history` Table - DONE

*   **Files to Edit:**
    *   `src/core/history/user_history_manager.py`
    *   (Manual/Scripted DB Change): `student_profile.db` schema.
*   **High-Level Changes:**
    1.  **Schema Change:** Add a new column `cloud_report_viewed_timestamp` (DATETIME, NULLABLE) to the `answer_history` table in `student_profile.db`. This column will store the timestamp when a user views the detailed cloud report.
    2.  **DB Manager Method:** Create a new method `mark_report_as_viewed(self, history_id: int) -> bool` in `UserHistoryManager`. This method will execute an SQL UPDATE statement to set the `cloud_report_viewed_timestamp` to the current time for the given `history_id`.
*   **Testing:**
    1.  Verify the `answer_history` table schema includes the new `cloud_report_viewed_timestamp` column.
    2.  Call `UserHistoryManager.mark_report_as_viewed(some_history_id)`.
    3.  Query `student_profile.db` directly to confirm that `cloud_report_viewed_timestamp` is set (not NULL) for `some_history_id`.
    4.  Ensure the method returns `True` on successful update and `False` if the `history_id` doesn't exist or an error occurs.

## Task 2: Update "New Report Count" Logic

*   **Files to Edit:**
    *   `src/core/history/user_history_manager.py`
*   **High-Level Changes:**
    1.  Modify the existing `get_new_report_count(self) -> int` method in `UserHistoryManager`.
    2.  The SQL query within this method should now count rows from `answer_history` where `cloud_report_received = TRUE` AND `cloud_report_viewed_timestamp IS NULL`.
*   **Testing:**
    1.  Ensure a test record in `answer_history` has `cloud_report_received = TRUE` and `cloud_report_viewed_timestamp IS NULL`. Call `get_new_report_count()`. Verify it returns `1` (or the correct count if multiple such records exist).
    2.  Update the same test record to have a non-NULL `cloud_report_viewed_timestamp`. Call `get_new_report_count()`. Verify it returns `0` (or the decremented count).
    3.  Ensure a record with `cloud_report_received = FALSE` is not counted, regardless of the `cloud_report_viewed_timestamp`.

## Task 3: Trigger Marking Report as "Viewed" from UI

*   **Files to Edit:**
    *   `src/ui/views/report_view.py` (Assumption: this is where detailed reports are displayed. If it's another view, that file needs editing).
*   **High-Level Changes:**
    1.  Identify the point in the UI code where the detailed cloud-generated report for a specific `history_id` is displayed to the user.
    2.  At this point, call `services.user_history_manager.mark_report_as_viewed(history_id)`.
    3.  Consider doing this only once per view session of that report, or if the `cloud_report_viewed_timestamp` is currently NULL for that `history_id`.
*   **Testing:**
    1.  Navigate to the UI view that displays a detailed report for a `history_id` that has `cloud_report_received = TRUE` and `cloud_report_viewed_timestamp IS NULL`.
    2.  After the report is displayed, check `student_profile.db` to confirm `cloud_report_viewed_timestamp` is now set for that `history_id`.
    3.  (Connects to Task 4) Observe if the "new reports" badge/count in the UI decrements.

## Task 4: Implement UI Badge/Indicator Update for New Reports

*   **Files to Edit:**
    *   `src/ui/main_window.py` (or the relevant profile/dashboard view where the indicator should live).
    *   `src/ui/views/question_view.py` (to trigger updates).
    *   Potentially other views that navigate away from/to the profile view.
*   **High-Level Changes:**
    1.  **Indicator Widget:** Add or identify a QLabel/widget in the main UI (e.g., next to "View Performance") that will display the count like "X/Y New Full Reports" or simply "X New".
    2.  **Update Function:** Create a method in the UI class managing this indicator (e.g., `update_new_reports_badge(self)`). This method will:
        *   Call `services.user_history_manager.get_new_report_count()`.
        *   Update the text of the indicator widget with the returned count.
    3.  **Trigger Points:**
        *   Call `update_new_reports_badge()` when the application starts or the main/profile view loads.
        *   In `QuestionView`, after `_handle_groq_feedback_result` successfully processes a cloud report (i.e., a new report has arrived), signal or directly call the `update_new_reports_badge()` method.
        *   When a report is marked as viewed (Task 3), ensure `update_new_reports_badge()` is called to refresh the count.
*   **Testing:**
    1.  Start the application with 0 new reports. Badge should show "0".
    2.  Simulate a new cloud report arriving for a `history_id` (set `cloud_report_received = TRUE`, `cloud_report_viewed_timestamp IS NULL` in DB). Trigger the UI update mechanism (e.g., by simulating the end of `_handle_groq_feedback_result`). The badge should update to "1".
    3.  Navigate to view that specific report (triggering Task 3). The badge should update back to "0".
    4.  Test with multiple reports arriving and being viewed.

## Task 5 (Revised): Implement Background Syncing of Preliminary Reports

This task ensures that preliminary reports (answered questions not yet processed by Groq) are picked up and processed in the background when the application is online.

### Task 5.1: Database Schema and Helper Method for `answer_history`

*   **Files to Edit:**
    *   (Manual/Scripted DB Change): `student_profile.db` schema.
    *   `src/core/history/user_history_manager.py`
*   **High-Level Changes:**
    1.  **Schema Change (DB):**
        *   Ensure the `answer_history` table in `student_profile.db` has a column:
            *   `cloud_sync_queued BOOLEAN DEFAULT FALSE` (Stores `0` or `1`). This flag indicates if the item has been picked up by the proactive background sync and added to the `QueueManager`'s JSON queue.
            *   *(Optional but Recommended)*: `cloud_sync_queue_timestamp DATETIME NULLABLE`. Timestamp for when it was added to the queue.
    2.  **`UserHistoryManager` Method - Get Pending Items:**
        *   Create/Refine method `get_pending_cloud_analysis_items(self, limit: int = 10) -> List[Tuple[int, str]]`.
        *   This method queries `answer_history` for rows where `cloud_report_received = FALSE` AND (`cloud_sync_queued = FALSE` OR `cloud_sync_queued IS NULL`).
        *   It returns a list of tuples, each `(history_id, cached_question_id)`.
    3.  **`UserHistoryManager` Method - Get Student Answer:**
        *   Create method `get_user_answer_json(self, history_id: int) -> Optional[str]`.
        *   This method retrieves the `user_answer_json` string for a given `history_id` from `answer_history`.
    4.  **`UserHistoryManager` Method - Mark as Queued:**
        *   Implement the existing placeholder `mark_as_queued_for_cloud(self, history_id: int) -> bool`.
        *   This method should UPDATE `answer_history` to set `cloud_sync_queued = TRUE` (and optionally `cloud_sync_queue_timestamp`) for the given `history_id`.
*   **Testing (Task 5.1):**
    1.  **DB Schema:** Verify `answer_history` has `cloud_sync_queued` (and optionally `cloud_sync_queue_timestamp`).
    2.  **`get_pending_cloud_analysis_items`:**
        *   Create test data:
            *   Item 1: `cloud_report_received = FALSE`, `cloud_sync_queued = FALSE`.
            *   Item 2: `cloud_report_received = FALSE`, `cloud_sync_queued = TRUE`.
            *   Item 3: `cloud_report_received = TRUE`.
        *   Call `get_pending_cloud_analysis_items()`. Verify it returns only Item 1 (history_id and cached_question_id).
    3.  **`get_user_answer_json`:**
        *   For a known `history_id` with a `user_answer_json` value, call the method and verify the correct JSON string is returned.
        *   Test with a non-existent `history_id` (should return `None`).
    4.  **`mark_as_queued_for_cloud`:**
        *   Call on a `history_id` where `cloud_sync_queued` is `FALSE`. Verify the method returns `True` and the DB is updated (`cloud_sync_queued` becomes `TRUE`, timestamp is set).
        *   Call on a non-existent `history_id`. Verify it returns `False`.

### Task 5.2: Data Retrieval Methods from `CacheManager` (or `UserOperations`)

*   **Files to Edit:**
    *   `src/data/cache/cache_manager.py` (preferred for SQLAlchemy interactions with `cached_questions` and `cached_answers` tables in `student_profile.db`) OR
    *   `src/data/database/operations.py` (if it's already handling these SQLAlchemy queries).
*   **High-Level Changes:**
    1.  **Method `get_question_details_by_key`:**
        *   Ensure/Create a method like `get_question_details_by_key(self, unique_question_key: str) -> Optional[Dict]` in the appropriate manager.
        *   This method takes a `unique_question_key` (which is `cached_question_id` from `answer_history`).
        *   It queries the `cached_questions` table and returns a dictionary representation of the `CachedQuestion` object (or the necessary fields like `content`, `marks`, `subject`, `level`, `topic`, `subtopic`).
    2.  **Method `get_correct_answer_details`:**
        *   Ensure/Create a method like `get_correct_answer_details(self, unique_question_key: str) -> Optional[Dict]` in the appropriate manager.
        *   This method takes a `unique_question_key`.
        *   It queries the `cached_answers` table and returns the `answer_content` dictionary for the corresponding question.
*   **Testing (Task 5.2):**
    1.  **`get_question_details_by_key`:**
        *   For a known `unique_question_key` in `cached_questions`, call the method and verify the returned dictionary contains the correct question text, marks, etc.
        *   Test with a non-existent key (should return `None`).
    2.  **`get_correct_answer_details`:**
        *   For a known `unique_question_key` that has a corresponding entry in `cached_answers`, call the method and verify the returned dictionary is the correct answer content.
        *   Test with a non-existent key (should return `None`).

### Task 5.3: Implement Proactive Background Sync Logic in `SyncService`

*   **Files to Edit:**
    *   `src/core/network/sync_service.py`
    *   `src/core/ai/marker.py` (potentially to expose or adapt prompt generation logic if `run_ai_evaluation` is not directly reusable as is).
*   **High-Level Changes:**
    1.  **New `SyncService` Method:** Create `_check_and_queue_pending_reports(self)`.
    2.  **Trigger `_check_and_queue_pending_reports`:** Call this new method from the `SyncService`'s main processing loop (e.g., `_sync_loop` or `_process_queue`) when the network is online and the service is not already busy with critical tasks. Also, consider calling it once when `SyncService.start()` is invoked and network is online.
    3.  **Logic for `_check_and_queue_pending_reports`:**
        *   Call `services.user_history_manager.get_pending_cloud_analysis_items()` to get a batch of items `(history_id, cached_question_id)`.
        *   For each item:
            *   Call `services.user_history_manager.get_user_answer_json(history_id)`.
            *   Call `services.cache_manager.get_question_details_by_key(cached_question_id)`.
            *   Call `services.cache_manager.get_correct_answer_details(cached_question_id)`.
            *   If all data is retrieved successfully:
                *   Construct the prompt: Use the retrieved question data, student answer (parsed from JSON), and correct answer data. This will involve calling your existing prompt templating logic (e.g., a refactored part of `run_ai_evaluation` or a new utility function that takes this data and returns the prompt string).
                *   If a valid prompt is generated:
                    *   Call `self.queue_cloud_analysis(history_id, prompt_for_groq)`.
                    *   Call `services.user_history_manager.mark_as_queued_for_cloud(history_id)` to prevent this item from being picked up again by this proactive check.
*   **Testing (Task 5.3):**
    1.  **Scenario 1 (Offline then Online):**
        *   Start app offline. Answer a question. `cloud_report_received` = FALSE, `cloud_sync_queued` = FALSE.
        *   Bring app online.
        *   Verify logs: `SyncService` calls `_check_and_queue_pending_reports`. It finds the item. Logs show it fetching data, constructing prompt, calling `queue_cloud_analysis`, and `mark_as_queued_for_cloud`.
        *   Verify `answer_history`: `cloud_sync_queued` becomes TRUE.
        *   Verify `sync_queue.json`: The item is added.
        *   Eventually, `_sync_cloud_analysis_request` processes it, calls Groq, updates `answer_history` (`cloud_report_received = TRUE`), and removes from `sync_queue.json`.
    2.  **Scenario 2 (Multiple Pending):**
        *   Create several preliminary reports in the DB (`cloud_report_received = FALSE`, `cloud_sync_queued = FALSE`).
        *   Start app online. Verify `_check_and_queue_pending_reports` picks them up (respecting its internal limit) and queues them.

### Task 5.4: (Verification) `QuestionView.trigger_cloud_sync` Refinement

*   This task was previously part of "Task 5" and involved adding a check in `QuestionView.trigger_cloud_sync` to call `services.user_history_manager.is_cloud_report_received(history_id)` and return early if `True`.
*   **Verify:** Ensure this check is robust and correctly prevents immediate re-processing by `QuestionView` if a report for that `history_id` has already been generated (perhaps by the background sync).
