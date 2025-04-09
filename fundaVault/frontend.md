# FundaVault Admin Device Registration Guide

This document outlines the process for registering client devices via the FundaVault admin API endpoints.

## API Endpoints & Authentication

1.  **What is the correct endpoint for admin device registration?**
    *   The endpoint is `POST /api/v1/admin/register-device`.

2.  **What authentication is required?**
    *   Admin authentication is required. Include a valid Admin JWT token in the `Authorization` header:
        ```
        Authorization: Bearer <your_admin_jwt_token>
        ```
    *   No other specific headers are needed.

## Request Format

3.  **What is the expected JSON request body?**
    *   The request uses the user's `email` to identify them. If the email doesn't exist, a new user is created using the provided details.

    ```json
    {
      "hardware_id": "string (Unique Hardware Identifier)",
      "email": "user@example.com",
      "full_name": "string (Required if creating a new user)",
      "address": "string (Required if creating a new user)",
      "city": "string (Required if creating a new user)",
      "country": "string (Required if creating a new user)"
    }
    ```

4.  **Are there specific validation rules for `hardware_id`?**
    *   It's treated as a string. No specific format (like UUID) is enforced by the API.
    *   The API *does* check for uniqueness. Sending a `hardware_id` that already exists will result in an error.

5.  **How is the user identified? How can admins find user info?**
    *   The user is identified by their `email` (string) in the request body, **not** a `user_id`.
    *   The backend finds the user by email or creates a new one if the email is not found.
    *   Admins can fetch a list of all users and their details (including `id`, `email`, `full_name`) using the `GET /api/v1/admin/users` endpoint (requires admin authentication).

## Response Format

6.  **What are the expected responses?**
    *   **Successful Registration (HTTP 201 Created):**
        ```json
        {
          "message": "Device registered successfully",
          "hardware_id": "string",
          "user_id": integer, // ID of the associated user (found or created)
          "email": "string"
        }
        ```
    *   **Duplicate Hardware ID (HTTP 409 Conflict):**
        ```json
        {
          "detail": "Hardware ID already registered."
        }
        ```
    *   **User Already Has Active Device (HTTP 409 Conflict):**
        ```json
        {
          "detail": "User already has an active device registered."
        }
        ```
    *   **Authentication/Authorization Error (HTTP 401/403):** Standard HTTP error responses.
    *   **Internal Server Error (HTTP 500):**
        ```json
        {
          "detail": "Device registration failed due to an internal error."
        }
        ```

## Additional User Information

7.  **What user details should be displayed in the admin UI?**
    *   To help admins select the correct user (if needed before registration) or verify details, the UI should display information obtained from `GET /api/v1/admin/users`. Key fields to show are:
        *   `id`
        *   `email`
        *   `full_name`
        *   `is_active`
    *   Subscription status can be fetched separately via `GET /api/v1/admin/subscriptions`.

8.  **Is there a maximum number of devices per user?**
    *   Yes, the current implementation enforces a limit of **one active device per user**. An attempt to register a device for a user who already has an active one will result in a 409 Conflict error.
