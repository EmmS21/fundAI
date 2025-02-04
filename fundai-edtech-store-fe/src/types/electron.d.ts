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
  clearAuth: () => Promise<boolean>;
  updateUserStatus: (userId: string, status: 'active' | 'inactive') => Promise<boolean>;
  deleteUser: (userId: string) => Promise<boolean>;
  getUsers: () => Promise<User[]>;
  syncApps: () => Promise<{ updated: boolean; count?: number; error?: string }>;
}

declare global {
  interface Window {
    electronAPI: ElectronAPI | jest.Mocked<ElectronAPI>;
  }
}
