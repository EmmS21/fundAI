# AI Marking Feature Checklist

- [ ] **Identify Cache Structure:** Determine how the correct answer and question are stored in the cache and how to retrieve them.
- [ ] **Frontend Logic:** Implement logic to capture the question ID, user's answer, and any initial marks upon submission.
- [ ] **Backend Endpoint:** Create a new backend endpoint (e.g., `/api/mark_answer`) to handle the marking request.
- [ ] **Data Retrieval (Backend):** Retrieve the specific question and its correct answer from the cache using the provided ID.
- [ ] **JSON Payload Creation:** Construct the JSON payload including the question, correct answer, user's answer, and marks.
- [ ] **Prompt Engineering:** Design the prompt for the local deepseek model, instructing it on how to mark, provide feedback, and suggest improvements.
- [ ] **Deepseek API Integration:** Implement the call to the local deepseek model's API, sending the JSON payload and prompt.
- [ ] **API Request/Response Handling:** Manage the API request lifecycle (send, wait, handle response/errors).
- [ ] **Response Processing:** Parse the deepseek model's response (marks, feedback, suggestions).
- [ ] **Frontend Display:** Update the UI to show the AI-generated feedback and suggestions to the user.
- [ ] **Error Handling:** Implement robust error handling for cache misses, API errors, etc.
- [ ] **Testing:** Test the feature end-to-end with various scenarios.
