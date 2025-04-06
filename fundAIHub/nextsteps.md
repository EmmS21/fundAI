# Frontend Changes for Secure Firebase Operations (Using Backend Proxy)

This document outlines the necessary modifications for the Electron/Vite frontend application to securely interact with Firebase using the new backend proxy (`fundAIHub`). The primary goal is to **remove sensitive Firebase service account credentials** from the client-side code and rely on the backend for administrative operations.

## 1. `.env` File Modifications

Yes, you should modify the `.env` file used by Vite for the frontend build to **remove the sensitive credentials**. However, some Firebase-related variables are still needed for client-side functionality (like user authentication).

**A. REMOVE the following variables entirely:**

These variables contain the sensitive Service Account Key information, which is now securely handled by the `fundAIHub` backend. They **MUST NOT** remain in the frontend code or `.env` file.

*   `VITE_FIREBASE_CLIENT_EMAIL`: No longer needed on the client.
*   `VITE_FIREBASE_PRIVATE_KEY`: **Critically important to remove.** This should never be in client code.
*   `VITE_FIREBASE_AUTH_PROVIDER_CERT_URL`: No longer needed on the client.
*   `VITE_FIREBASE_CLIENT_CERT_URL`: No longer needed on the client.

**B. KEEP (and verify) the following variables:**

These variables contain **public** configuration details needed by the standard Firebase *client-side* SDKs (e.g., `firebase/auth`) to identify your project and allow users to log in. They do **not** grant administrative access on their own.

*   `VITE_FIREBASE_PROJECT_ID`: Identifies your Firebase project. The client SDK needs this.
    *   Example: `VITE_FIREBASE_PROJECT_ID=adalchemyai-432120`
*   `VITE_FIREBASE_API_KEY`: This is the **Web API Key** (find it in Firebase project settings -> General). It's used by client-side SDKs like Firebase Auth to connect to your project's authentication services.
    *   *Action:* Ensure this variable exists and holds the correct **Web API Key** value. If you were previously using `VITE_GOOGLE_CLIENT_SECRET` for this purpose, **rename it to `VITE_FIREBASE_API_KEY`** in both the `.env` file and your frontend code (`src/config/firebase.ts`) for clarity and correctness.
    *   Example: `VITE_FIREBASE_API_KEY=AIzaSyA7A_tx7F6xVMb2sp9E8kQizGW7N3lINTs` (Replace with your actual key)

**Resulting `.env`:** After these changes, your `.env` file (relevant to Firebase) should *only* contain `VITE_FIREBASE_PROJECT_ID` and `VITE_FIREBASE_API_KEY`.

## 2. Update Firebase Configuration (`src/config/firebase.ts`)

Modify the Firebase initialization code (`src/config/firebase.ts`) to use *only* the public configuration values (`apiKey` and `projectId`) obtained from the updated `.env` file. Remove any code that attempts to use `clientEmail`, `privateKey`, or related certificate URLs.

**Example `src/config/firebase.ts` (Reflects `.env` changes):**

```typescript
import { initializeApp, FirebaseApp } from "firebase/app";
// Import only the specific client-side modules you use (e.g., Auth)
import { getAuth, Auth } from "firebase/auth";
// Import Firestore ONLY if you intend to use it *directly* from the client
// subject to Security Rules (NOT for admin operations).
// import { getFirestore, Firestore } from "firebase/firestore";

// Ensure VITE_FIREBASE_API_KEY and VITE_FIREBASE_PROJECT_ID are correctly loaded from your .env
const firebaseApiKey = import.meta.env.VITE_FIREBASE_API_KEY;
const firebaseProjectId = import.meta.env.VITE_FIREBASE_PROJECT_ID;

if (!firebaseApiKey || !firebaseProjectId) {
  console.error("Firebase API Key or Project ID is missing in environment variables!");
  // Handle this error appropriately - maybe show an error message to the user
  // or prevent the app from initializing further.
}

const firebaseConfig = {
  apiKey: firebaseApiKey,
  authDomain: `${firebaseProjectId}.firebaseapp.com`,
  projectId: firebaseProjectId,
  storageBucket: `${firebaseProjectId}.appspot.com`,
  // Add messagingSenderId or appId if needed for FCM/Analytics
};

// Initialize Firebase client-side SDK
let app: FirebaseApp | null = null;
let auth: Auth | null = null;
// let db: Firestore | null = null; // Only if using client-side Firestore

try {
  app = initializeApp(firebaseConfig);
  // Initialize only the services needed on the client
  auth = getAuth(app); // Example: Initialize Auth

  // Initialize Firestore client-side SDK ONLY if using client-side access governed by Security Rules.
  // For actions requiring admin privileges, you will call the backend API instead.
  // db = getFirestore(app);

  console.log("Firebase client SDK initialized successfully.");

} catch (error) {
  console.error("Failed to initialize Firebase client SDK:", error);
  // Handle initialization error
}


// Export the necessary client-side instances
// Check for null before exporting if initialization might fail
export { app, auth /*, db */ }; // Export 'db' only if using client-side Firestore access

```

**Key Changes:**

*   Uses **only** `VITE_FIREBASE_API_KEY` and `VITE_FIREBASE_PROJECT_ID` from `.env`.
*   Includes basic error checking for missing environment variables.
*   No `clientEmail`, `privateKey`, or certificate URLs are referenced.
*   Initializes only the *client-side* Firebase SDKs needed (like `getAuth`). **Do NOT attempt to initialize the Admin SDK here.**

## 3. Replace Admin Operations with Backend API Calls

**Instructions for the Frontend Engineer:**

You no longer have direct administrative access to Firebase from the frontend. Any operation that requires bypassing security rules or using admin privileges (like modifying arbitrary user data in Firestore, minting custom tokens with the Admin SDK, etc.) **must now be performed by calling the `fundAIHub` backend API.**

**Steps:**

1.  **Identify Operations:** Find all code sections that used the old service account credentials or performed actions intended only for administrators.
2.  **Find Backend Endpoints:** Consult the backend documentation or team to get the specific API endpoint URLs provided by `fundAIHub` for these tasks (e.g., `/api/secure/firestore-write`, `/api/admin/get-user-data/:userId`).
3.  **Implement API Calls:**
    *   Use `fetch` or a similar HTTP client library.
    *   **Electron IPC:** The recommended pattern is to trigger these calls from the renderer process using `ipcRenderer.invoke` and handle the actual `fetch` call within an `ipcMain.handle` listener in the main process (`electron/main.js`). This centralizes backend communication and avoids potential CORS issues.
4.  **Authentication:**
    *   Obtain the user's JWT token provided by FundaVault after they log in.
    *   For every request to a secure backend endpoint, include this token in the `Authorization` header:
        ```
        Authorization: Bearer <your_fundavault_jwt_token>
        ```
    *   The backend (`fundAIHub`) uses this token to verify the user's identity and permissions before executing the admin operation.
5.  **Handle Responses:** Process the success or error responses from the backend API accordingly in the frontend UI.

**Example Flow (Conceptual):**

*   **Renderer:** User clicks "Save Admin Setting". Component calls `ipcRenderer.invoke('save-admin-setting', { setting: 'value' })`.
*   **Preload:** Exposes `contextBridge.exposeInMainWorld('electronAPI', { saveAdminSetting: (data) => ipcRenderer.invoke('save-admin-setting', data) })`.
*   **Main Process:** `ipcMain.handle('save-admin-setting', async (event, payload) => { ... })` listener triggers.
    *   Gets the user's FundaVault token.
    *   Calls `fetch('BACKEND_URL/api/secure/admin-settings', { method: 'POST', headers: { 'Authorization': \`Bearer ${token}\`, ... }, body: JSON.stringify(payload) })`.
    *   Handles the backend's response.
    *   Returns the result (or throws an error) to the renderer.
*   **Renderer:** Receives the result/error from `invoke` and updates the UI.

By following these steps, the frontend application remains secure, delegating sensitive operations to the trusted backend, while still utilizing client-side Firebase services like Authentication where appropriate.