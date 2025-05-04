# AI Sync Feature - Cloud Analysis and Reporting

## Goal

To implement a secondary, asynchronous AI analysis feature where user interactions (question, user answer, correct answer) are sent to a powerful cloud-based AI model for a more comprehensive report, which is then stored in a cloud database for long-term progress tracking and analysis.

## Context & Existing Components

*   **Local Feedback:** Currently, after a user answers, `src/core/ai/marker.py` generates local feedback (Grade, Rationale, Study Topics).
*   **Local History Storage:** This local feedback, along with the question details and user answer, is stored locally in the `answer_history` table within `student_profile.db` via `UserHistoryManager`.
*   **Queueing System:** A persistent queue (`sync_queue.json`) managed by `QueueManager` (`src/core/queue_manager.py`) exists.
*   **Sync Service:** A background `SyncService` (`src/core/network/sync_service.py`) processes items from the queue when online, handling retries and different item types.

## Proposed Data Flow

1.  **User Answers:** User submits an answer in `QuestionView`.
2.  **Local AI Feedback:** `AIFeedbackWorker` runs `run_ai_evaluation`.
3.  **Local Storage:** `_handle_ai_feedback_result` calls `UserHistoryManager.add_history_entry` to save the interaction (Q, User A, Local AI Feedback) to the `answer_history` table (returns `history_id`).
4.  **Queue for Cloud Sync:** `_handle_ai_feedback_result` (or a related function) prepares the necessary data (including `history_id`, question data, user answer dict, correct answer data) and calls `services.queue_manager.add_to_queue(...)` with a specific `item_type` (e.g., `cloud_analysis_request`) and `priority`. `UserHistoryManager.mark_as_queued_for_cloud(history_id)` is called.
5.  **Sync Service Processing:** `SyncService` picks up the queued item when online.
6.  **Cloud AI Call:** The corresponding handler function in `SyncService` makes an API call to the designated large AI model (e.g., Groq API) with the interaction data. `UserHistoryManager.mark_as_sent_to_cloud(history_id)` is called upon successful sending.
7.  **Cloud Report Generation:** The cloud AI processes the data and generates a full report.
8.  **Cloud DB Storage:** The `SyncService` handler (or the cloud endpoint itself) stores the generated report in a designated cloud database (e.g., Firestore, MongoDB Atlas) linked to the user/hardware ID and potentially the `history_id`.
9.  **(Optional) Update Local App:** The cloud DB/endpoint could notify the local app (e.g., via Firebase function, webhook, or the SyncService polling) that the report is ready.
10. **Update Local History:** Upon notification (or successful cloud storage confirmation), `UserHistoryManager.update_with_cloud_report(history_id, cloud_report_data)` is called to update the `answer_history` table flags (`cloud_report_received`, `cloud_report_received_timestamp`) and store the cloud report details (`cloud_ai_...` columns).

## Implementation Steps

1.  **Define Cloud Report:** Specify the exact content and structure expected from the cloud AI report. What analysis should it provide beyond the local AI?
2.  **Define Queue Item Data:** Finalize the exact data structure to be added to the `QueueManager`. Ensure it includes the `history_id` from `answer_history`.
3.  **Choose `item_type` & Priority:** Decide on a unique `item_type` string (e.g., `'cloud_analysis_request'`) and an appropriate `QueuePriority` (e.g., `HIGH` or `MEDIUM`).
4.  **Implement Queuing Logic:** Modify `QuestionView._handle_ai_feedback_result` (or delegate to another controller) to gather the required data and call `services.queue_manager.add_to_queue()` after successfully saving the local history entry. Call `UserHistoryManager.mark_as_queued_for_cloud()`.
5.  **Implement `SyncService` Handler:**
    *   Add the new `item_type` to the processing logic in `SyncService._process_item`.
    *   Create a new handler function (e.g., `_sync_cloud_analysis_request`).
    *   Implement API call logic within the handler to interact with the chosen cloud AI service (e.g., Groq). Handle authentication, request formatting, and response parsing. Call `UserHistoryManager.mark_as_sent_to_cloud()`.
    *   Implement logic to send the generated report to the cloud database. Handle potential errors.
6.  **Implement Cloud Database Interaction:**
    *   Set up the cloud database schema/structure.
    *   Implement functions (likely within the `SyncService` handler or a separate cloud interaction module) to write the report data to the cloud database.
7.  **Implement `UserHistoryManager` Update Methods:**
    *   Implement `mark_as_queued_for_cloud`, `mark_as_sent_to_cloud`, and `update_with_cloud_report` methods in `UserHistoryManager` to perform the necessary `UPDATE` SQL operations on the `answer_history` table.
8.  **(Optional) Implement Local Update/Display:** If the cloud report needs to be visible in the app, implement the mechanism for receiving notification/data and updating the UI accordingly.

## Open Questions/Decisions

*   What is the specific value/content proposition of the cloud report compared to the local one? (Drives prompt engineering for the cloud AI).
*   Which specific cloud AI API will be used (Groq, OpenAI, Gemini, etc.)?
*   Which cloud database technology will be used (Firestore, MongoDB Atlas, etc.)?
*   How will the application be notified that a cloud report is ready (if needed)? Push notification? Polling? Trigger within SyncService success handler?
*   Error handling strategy for failed cloud AI calls or cloud DB writes. Should they be retried via the queue?
