## Requirements & Questions for User Subscription Activation

**Feature:** Admin needs to activate a 1-month subscription for a specific user.

**Client Implementation:**
- Added "Edit/Subscribe" button to user rows in `UsersTable`.
- Clicking the button opens `EditUserModal` showing user details.
- `EditUserModal` has an "Activate Subscription (1 Month)" button.
- Clicking this button needs to trigger an IPC call (e.g., `admin:activateSubscription`) passing the `user.id`.

**Questions for Backend Team (FundAIHub):**

1.  **Endpoint:** What FundAIHub API endpoint should the Electron app call (via the main process) to activate/update a user's subscription? (e.g., `POST /api/admin/users/{user_id}/subscription`)
2.  **Request:**
    *   What method should be used (POST, PUT)?
    *   What headers are required (Admin Auth token)?
    *   What should the request body contain? Does it just need the user ID (from the URL path), or do we need to send `{ "duration_months": 1 }` or similar?
3.  **Response:**
    *   What is the success response (status code, body)?
    *   What are potential error responses (e.g., user not found, activation failed)?
4.  **Interaction with FundaVault:** Does this FundAIHub endpoint handle communicating the subscription update to FundaVault, or is that a separate step?
