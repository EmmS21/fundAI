import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(({ command, mode }) => {
  // Load env file based on `mode` in the current working directory
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src')
      }
    },
    define: {
      // Expose env variables
      'process.env': {
        VITE_FIREBASE_PROJECT_ID: JSON.stringify(env.VITE_FIREBASE_PROJECT_ID),
        VITE_FIREBASE_CLIENT_EMAIL: JSON.stringify(env.VITE_FIREBASE_CLIENT_EMAIL),
        VITE_FIREBASE_PRIVATE_KEY: JSON.stringify(env.VITE_FIREBASE_PRIVATE_KEY),
        VITE_FIREBASE_AUTH_PROVIDER_CERT_URL: JSON.stringify(env.VITE_FIREBASE_AUTH_PROVIDER_CERT_URL),
        VITE_FIREBASE_CLIENT_CERT_URL: JSON.stringify(env.VITE_FIREBASE_CLIENT_CERT_URL),
        VITE_GOOGLE_CLIENT_SECRET: JSON.stringify(env.VITE_GOOGLE_CLIENT_SECRET),
      }
    }
  }
})
