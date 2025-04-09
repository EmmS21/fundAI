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
  adminRegisterDevice: (deviceData) => ipcRenderer.invoke('admin:register-device', deviceData),
  
  // Download Progress
  onDownloadProgress: (callback) => 
    ipcRenderer.on('download:progress', callback),
  onDownloadComplete: (callback) => 
    ipcRenderer.on('download:complete', callback),

  // User Operations
  getUsers: () => ipcRenderer.invoke('user:get-all'),
  updateUserStatus: (userId, status) => ipcRenderer.invoke('user:update-status', userId, status),
  deleteUser: (userId) => ipcRenderer.invoke('user:delete', userId),

  // Book Operations
  getBooks: () => ipcRenderer.invoke('books:getBooks'),

  // Auto Updater Methods
  onUpdateAvailable: (callback) => ipcRenderer.on('update_available', (_event, ...args) => callback(...args)),
  onUpdateProgress: (callback) => ipcRenderer.on('update_progress', (_event, ...args) => callback(...args)),
  onUpdateDownloaded: (callback) => ipcRenderer.on('update_downloaded', (_event, ...args) => callback(...args)),
  onUpdateError: (callback) => ipcRenderer.on('update_error', (_event, ...args) => callback(...args)),
  restartApp: () => ipcRenderer.send('restart_app'),
  removeAllUpdateListeners: () => {
    ipcRenderer.removeAllListeners('update_available');
    ipcRenderer.removeAllListeners('update_progress');
    ipcRenderer.removeAllListeners('update_downloaded');
    ipcRenderer.removeAllListeners('update_error');
  },
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
});
