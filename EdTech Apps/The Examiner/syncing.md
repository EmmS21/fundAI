# Full Report Generation & Notification Implementation Plan

This plan outlines the steps to fully implement the generation of full reports via Groq and notify the user of new, unread reports.

## Task 1: Implement "Viewed" Status Tracking in `answer_history` Table

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

## Task 5: (Refinement) Enhance Queue Trigger Logic in `QuestionView`

*   **Files to Edit:**
    *   `src/ui/views/question_view.py`
*   **High-Level Changes:**
    1.  In the `trigger_cloud_sync(self, history_id: int, local_prompt: str)` method:
        *   Before attempting to queue or start the `GroqFeedbackWorker`, add a call to `services.user_history_manager.is_cloud_report_received(history_id: int) -> bool`. (This new helper method will need to be created in `UserHistoryManager` to simply check the `cloud_report_received` flag for a given `history_id`).
        *   If `is_cloud_report_received()` returns `True`, log it and do not proceed with queueing or starting the worker for this `history_id`.
*   **Testing:**
    1.  Manually set `cloud_report_received = TRUE` for a specific `history_id` in `student_profile.db`.
    2.  Simulate the user submitting an answer that would normally trigger `trigger_cloud_sync` for this `history_id`.
    3.  Verify through logs or breakpoints that `sync_service.queue_cloud_analysis()` or `worker.start()` (for `GroqFeedbackWorker`) is *not* called for this `history_id`.
    4.  Repeat the test with `cloud_report_received = FALSE` and verify that the queueing/worker start *does* proceed.
