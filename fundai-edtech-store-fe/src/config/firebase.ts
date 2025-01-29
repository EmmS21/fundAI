import { initializeApp } from 'firebase/app';
import { getFirestore } from 'firebase/firestore';

console.log('Firebase Config Debug:', {
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  clientEmail: import.meta.env.VITE_FIREBASE_CLIENT_EMAIL,
  privateKeyExists: !!import.meta.env.VITE_FIREBASE_PRIVATE_KEY,
  authDomain: `${import.meta.env.VITE_FIREBASE_PROJECT_ID}.firebaseapp.com`,
});

const firebaseConfig = {
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  clientEmail: import.meta.env.VITE_FIREBASE_CLIENT_EMAIL,
  privateKey: import.meta.env.VITE_FIREBASE_PRIVATE_KEY?.replace(/\\n/g, '\n'),
  authDomain: `${import.meta.env.VITE_FIREBASE_PROJECT_ID}.firebaseapp.com`,
  storageBucket: `${import.meta.env.VITE_FIREBASE_PROJECT_ID}.appspot.com`,
  apiKey: import.meta.env.VITE_GOOGLE_CLIENT_SECRET,
  authProviderX509CertUrl: import.meta.env.VITE_FIREBASE_AUTH_PROVIDER_CERT_URL,
  clientX509CertUrl: import.meta.env.VITE_FIREBASE_CLIENT_CERT_URL,
  databaseURL: `https://${import.meta.env.VITE_FIREBASE_PROJECT_ID}.firebaseio.com`,
};

// Initialize Firebase
export const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);

// Optional: Add error handling
if (!import.meta.env.VITE_FIREBASE_PROJECT_ID) {
  throw new Error('Missing Firebase Project ID');
}

if (!import.meta.env.VITE_FIREBASE_PRIVATE_KEY) {
  throw new Error('Missing Firebase Private Key');
}

if (!import.meta.env.VITE_FIREBASE_CLIENT_EMAIL) {
  throw new Error('Missing Firebase Client Email');
}
