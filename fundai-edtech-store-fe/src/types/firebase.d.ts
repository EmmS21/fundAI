declare interface FirebaseConfig {
  projectId: string;
  clientEmail: string;
  privateKey: string | undefined;
  authDomain: string;
  storageBucket: string;
  apiKey: string;
  authProviderX509CertUrl: string;
  clientX509CertUrl: string;
  databaseURL: string;
}
