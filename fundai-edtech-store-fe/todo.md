# TODO: Secure Firebase Credentials using Backend Proxy

## 1. Understand the Security Problem

**Why:**
Storing sensitive credentials like Firebase Service Account Keys (specifically `private_key` and `client_email`) directly in the client-side code (loaded via `.env` and `src/config/firebase.ts`) is a major security vulnerability for a distributed Electron application.

**The Issue:**
- The frontend code (JavaScript) bundled by Vite is included in the packaged Electron application (`app.asar`).
- This packaged code can be extracted and inspected by users.
- If the Service Account Key is embedded, malicious users could extract it and gain **full administrative access** to the Firebase project (`adalchemyai-432120`), bypassing all security rules. This could lead to data breaches, unauthorized data modification/deletion, and unexpected costs.
- The `.env` file is meant for development convenience but does not provide security for secrets in a production build distributed to users.

## 2. The Solution: Backend Proxy Pattern

**How:**
Instead of the Electron app using sensitive credentials directly, it will delegate these operations to our trusted backend server (`fundaihubstore` or `fundavault` hosted on Render).

- The Electron app will only handle user interactions and make standard API calls to our backend.
- The backend server will securely store the Firebase Service Account Key as environment variables within the Render hosting environment.
- The backend will use the Firebase Admin SDK (initialized with the secure credentials) to perform the privileged Firebase operations requested by the Electron app.
- Secrets *never* leave the secure backend server environment.

## 3. Implementation Steps

**Task List:**

-   **[ ] Identify Sensitive Firebase Operations:**
    -   Audit the `src/` directory, especially `src/config/firebase.ts` and any files using `initializeApp` or Firebase SDK methods (`getFirestore`, `setDoc`, `getDoc`, etc.).
    -   Determine which operations absolutely require Service Account privileges (admin tasks, bypassing security rules) vs. operations that can use standard user authentication (Firebase Auth) or public access.

-   **[ ] Modify Frontend Firebase Configuration:**
    -   Edit `src/config/firebase.ts`.
    -   Remove `privateKey`, `clientEmail`, `authProviderX509CertUrl`, and `clientX509CertUrl` from the `firebaseConfig` object.
    -   Only keep public configuration like `apiKey`, `authDomain`, `projectId`, `storageBucket`.
    -   *(Optional but Recommended)* Rename `VITE_GOOGLE_CLIENT_SECRET` to `VITE_FIREBASE_API_KEY` in `.env` and `src/config/firebase.ts` for clarity.
    -   Remove the corresponding sensitive `VITE_` variables (`VITE_FIREBASE_PRIVATE_KEY`, `VITE_FIREBASE_CLIENT_EMAIL`, etc.) from the `.env` file used by Vite.

-   **[ ] Define Backend API Endpoints:**
    -   For each sensitive operation identified, define a new API endpoint specification (e.g., `POST /api/admin/update-user-data`, `GET /api/secure-content/:id`).
    -   Decide which backend service (`fundaihubstore` or `fundavault`) is more appropriate for each endpoint.

-   **[ ] Configure Backend Environment Variables:**
    -   Access the Render dashboard for the chosen backend service(s).
    -   Add the following environment variables securely:
        -   `FIREBASE_PROJECT_ID`: `adalchemyai-432120`
        -   `FIREBASE_CLIENT_EMAIL`: `firebase-adminsdk-f4odw@adalchemyai-432120.iam.gserviceaccount.com`
        -   `FIREBASE_PRIVATE_KEY`: (Copy the full private key value from the service account JSON, ensuring newlines are handled correctly by Render's environment variable input).

-   **[ ] Implement Backend Logic:**
    -   Add the Firebase Admin SDK dependency to the backend service (e.g., `go get firebase.google.com/go/v4`, `npm install firebase-admin`).
    -   Initialize the Firebase Admin SDK in the backend code, reading credentials from the environment variables configured above.
    -   Implement the API endpoint handlers defined earlier.
    -   Include necessary validation (e.g., check user's JWT token from FundaVault if the action requires specific user permissions).
    -   Use the Admin SDK to perform the required Firebase actions (Firestore reads/writes, Storage operations, etc.).
    -   Return appropriate responses to the client.

-   **[ ] Update Electron App Communication:**
    -   Modify the Electron app's code where sensitive Firebase operations were previously performed.
    -   Instead of calling Firebase SDK methods directly, use `fetch` (likely within the Electron `main` process, triggered via IPC from the `renderer` process) to call the new backend API endpoints.
    -   Update `electron/preload.js` and associated `ipcMain` handlers in `electron/main.js` if necessary to facilitate this communication.
    -   Ensure authentication tokens (e.g., from FundaVault login) are included in the API requests to the backend where needed.

-   **[ ] Testing:**
    -   Thoroughly test all functionality that was refactored to ensure the backend proxy works correctly.
    -   Verify that sensitive operations succeed when authorized and fail when not.
    -   Confirm that the packaged application no longer contains the sensitive Firebase credentials.
