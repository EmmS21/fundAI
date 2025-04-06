import { Book } from '../types/book';

// We assume window.electronAPI will be extended (in preload.js and electron.d.ts)
// to include a getBooks method.
declare global {
  interface Window {
    electronAPI: {
      // Include existing methods from your preload.js/electron.d.ts
      getApps: () => Promise<any[]>;
      adminLogin: (credentials: any) => Promise<any>;
      getUsers: () => Promise<any[]>;
      // ... other existing methods

      // Add the new method for fetching books
      getBooks: () => Promise<Book[]>;
    };
  }
}

export const bookService = {
  /**
   * Fetches the list of books by requesting them from the backend
   * via Electron's main process IPC.
   */
  async getBooks(): Promise<Book[]> {
    // Check if the electronAPI and the getBooks method exist before calling
    if (window.electronAPI && typeof window.electronAPI.getBooks === 'function') {
      try {
        console.log("Requesting books from backend via window.electronAPI.getBooks()");
        // This triggers the IPC call defined in preload.js ('books:getBooks')
        const booksData = await window.electronAPI.getBooks();

        // Basic validation or mapping can happen here if needed
        // e.g., converting date strings from JSON to Date objects
        console.log("Received books via IPC:", booksData);
        return booksData;

      } catch (error) {
        console.error("Failed to fetch books via Electron IPC (window.electronAPI.getBooks):", error);
        return []; // Return empty array on error
      }
    } else {
      console.error("window.electronAPI.getBooks is not available. Check preload.js and contextBridge setup.");
      return []; // Return empty array if the API is not available
    }
  }
};
