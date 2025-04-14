const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Store Operations
  getApps: () => ipcRenderer.invoke('store:getApps'),
  getAppDetails: (appId) => ipcRenderer.invoke('store:getAppDetails', appId),
  downloadApp: (args) => ipcRenderer.invoke('store:downloadApp', args),
  syncApps: () => ipcRenderer.invoke('store:syncApps'),
  
  // Auth Operations
  login: (credentials) => ipcRenderer.invoke('auth:login', credentials),
  adminLogin: (credentials) => ipcRenderer.invoke('auth:adminLogin', credentials),
  checkAdmin: () => ipcRenderer.invoke('auth:checkAdmin'),
  clearAuth: () => ipcRenderer.invoke('auth:clearAuth'),
  adminRegisterDevice: (deviceData) => ipcRenderer.invoke('admin:register-device', deviceData),
  
  // Download Progress
  onDownloadProgress: (callback) =>
    ipcRenderer.on('download-progress', (_event, ...args) => callback(...args)),
  onDownloadComplete: (callback) =>
    ipcRenderer.on('download-complete', (_event, ...args) => callback(...args)),
  onDownloadError: (callback) =>
    ipcRenderer.on('download-error', (_event, ...args) => callback(...args)),
  onDownloadCancelled: (callback) =>
    ipcRenderer.on('download-cancelled', (_event, ...args) => callback(...args)),

  // User Operations
  getUsers: () => ipcRenderer.invoke('user:get-all'),
  updateUserStatus: (userId, status) => ipcRenderer.invoke('user:update-status', userId, status),
  deleteUser: (userId) => ipcRenderer.invoke('user:delete', userId),
  updateUserSubscription: (userId, payload) => ipcRenderer.invoke('users:updateSubscription', userId, payload),
  deleteUserSubscription: (userId) => ipcRenderer.invoke('users:deleteSubscription', userId),
  subscribeUser: (userId) => ipcRenderer.invoke('user:subscribe', userId),

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

contextBridge.exposeInMainWorld('electron', {
  // Download Management
  onDownloadProgress: (callback) =>
    ipcRenderer.on('download-progress', callback),
  onDownloadComplete: (callback) =>
    ipcRenderer.on('download-complete', callback),
  onDownloadError: (callback) => ipcRenderer.on('download-error', callback),
  cancelDownload: (downloadUrl) =>
    ipcRenderer.send('cancel-download', downloadUrl),
  openFile: (filePath) => ipcRenderer.send('open-file', filePath),
  showItemInFolder: (filePath) =>
    ipcRenderer.send('show-item-in-folder', filePath),

  // Duplicate Download Handling (NEW)
  onDownloadDuplicateFound: (callback) => {
    ipcRenderer.on('download-duplicate-found', callback);
  },
  sendDownloadDuplicateResponse: (response) => {
    ipcRenderer.send('download-duplicate-response', response);
  },

  // General Listener Removal (Modified to be more generic)
  // Consider replacing specific onDownload* removals if you adopt this pattern widely
  removeListener: (channel, callback) => {
    ipcRenderer.removeListener(channel, callback);
  },
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  },

  // Provide specific listener removal if needed for this bridge
  removeDuplicateListener: (callback) => {
      ipcRenderer.removeListener('download-duplicate-found', callback);
  }
});

console.log('Preload script loaded.');
