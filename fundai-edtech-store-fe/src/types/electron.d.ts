export interface ElectronAPI {
  getApps: () => Promise<any[]>;
  getAppDetails: (appId: string) => Promise<any>;
  downloadApp: (appId: string) => Promise<void>;
  login: (credentials: { username: string; password: string }) => Promise<any>;
  onDownloadProgress: (callback: (event: any, progress: number) => void) => void;
  onDownloadComplete: (callback: (event: any, appId: string) => void) => void;
  adminLogin: (credentials: { 
    email: string; 
    password: string; 
  }) => Promise<{
    success: boolean;
    isAdmin?: boolean;
    token?: string;
    error?: string;
  }>;
  checkAdmin: () => Promise<boolean>;
}

declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}
