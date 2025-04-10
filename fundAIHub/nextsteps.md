# User Management API Endpoints

Here are the proposed API endpoints to support the user management actions requested by the frontend.

---

## 1. Edit User Details

*   **URL:** `/api/v1/users/{userId}`
*   **HTTP Method:** `PATCH`
*   **Description:** Updates specific details for a given user.
*   **Path Parameters:**
    *   `userId` (string): The unique identifier of the user to edit.
*   **Expected Request Body/Payload:** A JSON object containing the fields to update. Only include the fields being changed.
    ```json
    {
      "name": "New User Name",
      "email": "new.email@example.com"
      // Add other editable fields as needed
    }
    ```
*   **Expected Success Response (200 OK):** The full, updated user object.
    ```json
    {
      "id": "user_123",
      "name": "New User Name",
      "email": "new.email@example.com",
      "is_active": true,
      // ... other user fields
      "created_at": "...",
      "updated_at": "..."
    }
    ```
*   **Potential Error Responses:**
    *   `400 Bad Request`: Invalid request body format or data.
    *   `401 Unauthorized`: Missing or invalid authentication token.
    *   `403 Forbidden`: User does not have permission to edit this user.
    *   `404 Not Found`: User with the specified `userId` does not exist.
    *   `500 Internal Server Error`: Backend error.

---

## 2. Change Active Status

*   **URL:** `/api/v1/users/{userId}`
*   **HTTP Method:** `PATCH`
*   **Description:** Activates or deactivates a user account. This uses the same endpoint as editing general details.
*   **Path Parameters:**
    *   `userId` (string): The unique identifier of the user whose status is changing.
*   **Expected Request Body/Payload:**
    ```json
    {
      "is_active": true // or false
    }
    ```
*   **Expected Success Response (200 OK):** The full, updated user object reflecting the new status.
    ```json
    {
      "id": "user_123",
      "name": "User Name",
      "email": "user.email@example.com",
      "is_active": true, // updated status
      // ... other user fields
      "created_at": "...",
      "updated_at": "..."
    }
    ```
*   **Potential Error Responses:**
    *   `400 Bad Request`: Invalid request body format or data (`is_active` missing or not boolean).
    *   `401 Unauthorized`: Missing or invalid authentication token.
    *   `403 Forbidden`: User does not have permission to change the status of this user.
    *   `404 Not Found`: User with the specified `userId` does not exist.
    *   `500 Internal Server Error`: Backend error.

---

## 3. Manage Subscription

*   **URL:** `/api/v1/users/{userId}/subscription`
*   **HTTP Method:** `PUT` (to create or update/replace the subscription) or `DELETE` (to remove subscription)
*   **Description:** Manages the subscription associated with a user. `PUT` will assign or change the subscription plan. `DELETE` will remove any existing subscription.
*   **Path Parameters:**
    *   `userId` (string): The unique identifier of the user whose subscription is being managed.

*   **For `PUT` Request:**
    *   **Expected Request Body/Payload:** Details of the subscription being assigned/updated. The exact fields depend on your subscription model.
        ```json
        // Example: Assigning a specific plan
        {
          "plan_id": "pro_monthly", // Identifier for the subscription plan
          "status": "active" // e.g., 'active', 'trialing', 'cancelled'
          // Add other relevant fields like start/end dates if needed
        }
        ```
    *   **Expected Success Response (200 OK):** Details of the updated subscription or the updated user object with subscription info.
        ```json
        // Example: Returning subscription details
        {
          "user_id": "user_123",
          "plan_id": "pro_monthly",
          "status": "active",
          "start_date": "...",
          "end_date": "..." // or null if ongoing
        }
        ```

*   **For `DELETE` Request:**
    *   **Expected Request Body/Payload:** None.
    *   **Expected Success Response (204 No Content):** Indicates successful removal of the subscription.

*   **Potential Error Responses (Both Methods):**
    *   `400 Bad Request`: Invalid request body (for `PUT`), invalid `plan_id`, etc.
    *   `401 Unauthorized`: Missing or invalid authentication token.
    *   `403 Forbidden`: User does not have permission to manage subscriptions for this user.
    *   `404 Not Found`: User with the specified `userId` does not exist, or (for `DELETE`) no subscription exists to delete.
    *   `500 Internal Server Error`: Backend error.

---
