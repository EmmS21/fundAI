const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Store Operations
  getApps: () => ipcRenderer.invoke('store:getApps'),
  getAppDetails: (appId) => ipcRenderer.invoke('store:getAppDetails', appId),
  downloadApp: (appId) => ipcRenderer.invoke('store:downloadApp', appId),
  syncApps: () => ipcRenderer.invoke('store:syncApps'),
  
  // Auth Operations
  login: (credentials) => ipcRenderer.invoke('auth:login', credentials),
  adminLogin: (credentials) => ipcRenderer.invoke('auth:adminLogin', credentials),
  checkAdmin: () => ipcRenderer.invoke('auth:checkAdmin'),
  clearAuth: () => ipcRenderer.invoke('auth:clearAuth'),
  
  // Download Progress
  onDownloadProgress: (callback) => 
    ipcRenderer.on('download:progress', callback),
  onDownloadComplete: (callback) => 
    ipcRenderer.on('download:complete', callback),

  // User Operations
  getUsers: () => ipcRenderer.invoke('user:get-all'),
  updateUserStatus: (userId, status) => ipcRenderer.invoke('user:update-status', userId, status),
  deleteUser: (userId) => ipcRenderer.invoke('user:delete', userId),
});
