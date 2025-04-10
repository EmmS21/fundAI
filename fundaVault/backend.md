# FundaVault Backend API Documentation

This document outlines the API endpoints for the FundaVault backend, intended for use by the frontend development team.

**Base URL:** The API is hosted via Modal. The exact base URL will be provided upon deployment. All endpoint paths below should be appended to this base URL.

---

## Authentication

*(Documentation for authentication endpoints, like /api/v1/auth/device, would go here)*

---

## User Management

*(Documentation for user endpoints, like /api/v1/users/, would go here)*

---

## Subscription Management

These endpoints manage user subscriptions. Subscriptions currently last for 30 days.

### Create Subscription

*   **URL:** `/api/v1/subscriptions/{user_id}`
*   **Method:** `POST`
*   **Description:** Creates a new 30-day subscription for the specified user. Fails if the user already has an active subscription.
*   **Path Parameters:**
    *   `user_id` (integer): The ID of the user to create the subscription for.
*   **Request Body:** None
*   **Success Response (200 OK):**
    ```json
    {
      "message": "Subscription created",
      "user_id": 123,
      "start_date": "2023-10-27T10:00:00.000Z", // ISO 8601 format UTC
      "end_date": "2023-11-26T10:00:00.000Z"   // ISO 8601 format UTC
    }
    ```
*   **Error Responses:**
    *   `400 Bad Request`: "Subscription already exists"
    *   `500 Internal Server Error`: "Failed to create subscription: {error details}"

### Get Subscription Status

*   **URL:** `/api/v1/subscriptions/{user_id}/status`
*   **Method:** `GET`
*   **Description:** Checks the current status of a user's subscription.
*   **Path Parameters:**
    *   `user_id` (integer): The ID of the user whose subscription status to check.
*   **Request Body:** None
*   **Success Response (200 OK):**
    *   If active:
        ```json
        {
          "active": true,
          "end_date": "2023-11-26T10:00:00.000Z", // ISO 8601 format UTC
          "days_remaining": 25
        }
        ```
    *   If inactive or not found:
        ```json
        {
          "active": false,
          "reason": "No subscription found" // Or other reason if applicable
        }
        ```
*   **Error Responses:**
    *   `500 Internal Server Error`: "Failed to check subscription: {error details}"

### Renew Subscription

*   **URL:** `/api/v1/subscriptions/{user_id}/renew`
*   **Method:** `POST`
*   **Description:** Renews an existing subscription for another 30 days, extending the current `end_date`.
*   **Path Parameters:**
    *   `user_id` (integer): The ID of the user whose subscription to renew.
*   **Request Body:** None
*   **Success Response (200 OK):**
    ```json
    {
      "message": "Subscription renewed",
      "new_end_date": "2023-12-26T10:00:00.000Z" // ISO 8601 format UTC
    }
    ```
*   **Error Responses:**
    *   `404 Not Found`: "No subscription found"
    *   `500 Internal Server Error`: "Failed to renew subscription: {error details}"

---

## Device Management

*(Documentation for device endpoints, like admin registration, would go here)*

---

## Admin Endpoints

*(Documentation for admin-specific endpoints, like listing all users/devices/subscriptions, activating/deactivating users, etc., would go here)*
