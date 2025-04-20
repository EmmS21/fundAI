# AI Marking Feature Checklist

- [x] **Identify Cache Structure:** Determined structure (questions/answers JSONs). Answer saving logic added (pending confirmation).
- [x] **Frontend Logic:** Implemented capture of question ID, user answer, marks. Called placeholder AI function.
- [x] **Data Retrieval (Answers):** Implemented logic in frontend (`_submit_answer`) to load correct answer JSON.
- [ ] ~~JSON Payload Creation~~ **(N/A - Data passed directly to function)**
- [x] **Prompt Engineering:**
    - [x] Define role (Cambridge Examiner).
    - [x] Define input (question, user answer, correct answer, marks).
    - [x] Specify marking standards (strict, not pedantic).
    *   [x] Specify feedback requirements:
        *   [x] Mark Awarded.
        *   [x] Strengths/Weaknesses.
        *   [x] Understanding gap analysis.
        *   [x] *Specific* topic/subtopic study suggestions (based on gap).
        *   [x] *Contextual* self-reflection questions (based on gap).
        *   [x] Include correct answer in response.
        *   [x] Objective/strict understanding rating.
    - [x] Ensure parsable output structure (e.g., clear sections).
- [x] **Local Model Interaction (GGUF):**
    - [x] Implement model finding/loading (using appropriate library like `ctransformers` or `llama-cpp-python`, handling path configuration).
    - [x] Implement sending prompt and receiving response from loaded model (via `llama-server` and `requests`).
    - [x] Implement model stopping/unloading (via `subprocess.terminate/kill`).
- [ ] **Response Processing:** Parse the detailed AI response (mark, feedback, suggestions, rating, etc.) from the model.
- [ ] **Waiting UI:**
    - [ ] Implement non-blocking AI call (use `QThread`).
    - [ ] Display modal dialog (Spinner recommended first due to performance concerns).
    - [ ] Hide modal dialog upon receiving AI response or error.
- [ ] **Frontend Display:** Update the UI to show the parsed AI feedback, suggestions, rating, and correct answer to the user.
- [ ] **Error Handling:** Enhance error handling for AI model interaction (loading errors, generation errors, parsing errors) and UI updates.
- [ ] **Testing:** Test the feature end-to-end with various scenarios, including different answer qualities and potential errors.
