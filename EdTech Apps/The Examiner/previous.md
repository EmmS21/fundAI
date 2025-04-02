# Debugging the "No Exams Available" Status

**Problem:**
The UI component `SubjectCard` was incorrectly displaying the status "No Exams Available" immediately upon loading, even though the corresponding cached `.json` question files existed in the correct file system location (`src/data/cache/questions/<subject>/<level>/<year>/`).

**Debugging Process:**
1.  **Initial Hypothesis (Incorrect):** We initially suspected a timing issue, thinking the UI was checking the cache *before* the background caching process had finished writing the files. This was disproven by the fact that the files were confirmed to exist *before* the UI loaded.
2.  **Function Investigation:** We examined the functions responsible for checking cache status:
    *   `CacheManager._count_cached_questions`: We added logs here, but realized this function wasn't being called by the primary status display logic in the `SubjectCard` header.
    *   `CacheManager.get_subject_cache_status`: This function *was* being called by the `SubjectCard` header logic (`SubjectCard._update_header_status`). It was designed to check the file system for `.json` files.
3.  **Logging:** We added detailed logging inside `SubjectCard._update_header_status` and `CacheManager.get_subject_cache_status`.
4.  **Diagnosis via Logs:** The logs revealed the crucial issue:
    *   `get_subject_cache_status` correctly traversed the file system and counted the existing `.json` files (e.g., found 10 questions for Biology/o_level).
    *   However, the dictionary returned by `get_subject_cache_status` back to the `SubjectCard` was **missing the `'question_count'` key**.
    *   The UI code in `SubjectCard._update_header_status` used `cache_data.get('question_count', 0)`. Because the key was missing, it defaulted to `0`.
    *   This `0` count caused the UI logic to determine that no exams were available, even though the files were present and counted internally by the cache manager function.

**Solution:**
We made a minimal change to `src/data/cache/cache_manager.py` within the `get_subject_cache_status` function.

*   **Change:** Added the line `result['question_count'] = question_count` just before the `result` dictionary is returned.
*   **Why:** This ensures that the actual count of question files found on the file system is included in the status dictionary returned to the UI. The UI can then correctly use this count to determine and display the "Ready" status instead of defaulting to "No Exams Available".

This fix correctly links the file system check performed by the cache manager to the status display logic in the user interface.
