# Backend Issue: Invalid content ID on /api/downloads/start

**Status:** Authentication via FundaVault is now working correctly (previous `503` error resolved).

**Current Problem:** The `/api/downloads/start` endpoint is returning a `400 Bad Request` with the error message `"Invalid content ID"`.

## Context

1.  The Electron client (`electron/main.js`) initiates a download by sending a POST request to `/api/downloads/start`.
2.  The request includes the `Device-ID` header (verified successfully by FundaVault) and a JSON body: `{ "contentId": appId }`.
3.  The `appId` value is passed from the React frontend via IPC to the Electron main process.
4.  Despite successful authentication, the `/api/downloads/start` handler rejects the request with a `400` error, specifically citing the `contentId` as invalid.

## Frontend Logs (Electron `main.js`)

```
[Download] Sending contentId: [ACTUAL_APP_ID_VALUE] to /api/downloads/start 
[Download] Failed to start download: 400 - Invalid content ID
```

*Note: We've added logging on the client-side to confirm the exact `appId` value being sent.* 

## Request for Backend Team

Please investigate the `/api/downloads/start` endpoint handler:

1.  **Validation Logic:** Check the validation rules for the `contentId` field. What format/type is expected? Is it expecting a UUID, integer, or specific string pattern?
2.  **Data Lookup:** Verify how the received `contentId` is used to look up the corresponding content/app record in the database. Could the specific ID being sent be missing from the relevant table?
3.  **Error Handling:** Confirm that the "Invalid content ID" error is being generated under the correct circumstances.

Knowing the exact `appId` value logged by the client (which the user can provide) will be crucial for testing on the backend.
