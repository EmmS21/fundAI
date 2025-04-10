export interface ElectronAPI {
  getApps: () => Promise<any[]>;
  getAppDetails: (appId: string) => Promise<any>;
  downloadApp: (appId: string) => Promise<any>;
  login: (credentials: { username: string; password: string }) => Promise<any>;
  onDownloadProgress: (callback: (progress: ProgressInfo) => void) => void;
  onDownloadComplete: (callback: (result: { appId: string, path: string }) => void) => void;
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
  updateUserStatus: (userId: string, status: 'active' | 'inactive') => Promise<any>;
  deleteUser: (userId: string) => Promise<any>;
  getUsers: () => Promise<any[]>;
  syncApps: () => Promise<{ updated: boolean; count?: number; error?: string }>;
  getBooks: () => Promise<any[]>;
  onUpdateAvailable: (callback: (info: any) => void) => void;
  onUpdateProgress: (callback: (progress: any) => void) => void;
  onUpdateDownloaded: (callback: (info: any) => void) => void;
  onUpdateError: (callback: (errorMessage: string) => void) => void;
  restartApp: () => void;
  removeAllUpdateListeners: () => void;
  getAppVersion: () => Promise<string>;
  adminRegisterDevice: (deviceData: any) => Promise<any>;
  updateUserDetails: (userId: string, payload: UserDetailsPayload) => Promise<UpdatedUserResponse>;
  updateUserSubscription: (userId: string, payload: UserSubscriptionPayload) => Promise<UpdatedSubscriptionResponse>;
  deleteUserSubscription: (userId: string) => Promise<DeleteSubscriptionResponse>;
}

declare global {
  interface Window {
    electronAPI: ElectronAPI | jest.Mocked<ElectronAPI>;
  }
}
