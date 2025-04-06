import { initializeApp, FirebaseApp } from "firebase/app";
// Import only the specific client-side modules you use (e.g., Auth)
import { getAuth, Auth } from "firebase/auth";
// Import Firestore ONLY if you intend to use it *directly* from the client
// subject to Security Rules (NOT for admin operations).
// import { getFirestore, Firestore } from "firebase/firestore";

// Ensure VITE_FIREBASE_API_KEY (currently VITE_GOOGLE_CLIENT_SECRET) and VITE_FIREBASE_PROJECT_ID are correctly loaded from your .env
// TODO: Update variable name here if VITE_GOOGLE_CLIENT_SECRET is renamed in .env
const firebaseApiKey = import.meta.env.VITE_GOOGLE_CLIENT_SECRET;
const firebaseProjectId = import.meta.env.VITE_FIREBASE_PROJECT_ID;

if (!firebaseApiKey || !firebaseProjectId) {
  console.error(
    "Firebase API Key or Project ID is missing in environment variables!"
  );
  // Handle this error appropriately - maybe show an error message to the user
  // or prevent the app from initializing further.
  // For now, we'll throw to make it obvious during development
  throw new Error(
    "Missing Firebase configuration. Check .env file and variable names (VITE_GOOGLE_CLIENT_SECRET/VITE_FIREBASE_API_KEY, VITE_FIREBASE_PROJECT_ID)."
  );
}

const firebaseConfig = {
  apiKey: firebaseApiKey,
  authDomain: `${firebaseProjectId}.firebaseapp.com`,
  projectId: firebaseProjectId,
  storageBucket: `${firebaseProjectId}.appspot.com`,
  // Add messagingSenderId or appId if needed for FCM/Analytics
  // messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
  // appId: "YOUR_APP_ID",
  // measurementId: "YOUR_MEASUREMENT_ID" // If using Analytics
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
  // Depending on the app, might show error UI or quit
}

// Export the necessary client-side instances
// Check for null before exporting if initialization might fail
export { app, auth /*, db */ }; // Export 'db' only if using client-side Firestore access
