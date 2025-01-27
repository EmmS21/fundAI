const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Auth related
  login: (credentials) => ipcRenderer.invoke('auth:login', credentials),
  logout: () => ipcRenderer.invoke('auth:logout'),
  
  // Store related
  getApps: () => ipcRenderer.invoke('store:getApps'),
  getAppDetails: (appId) => ipcRenderer.invoke('store:getAppDetails', appId),
  
  // Download related
  startDownload: (appId) => ipcRenderer.invoke('download:start', appId),
  pauseDownload: (appId) => ipcRenderer.invoke('download:pause', appId),
  resumeDownload: (appId) => ipcRenderer.invoke('download:resume', appId),
  
  // Listeners
  onDownloadProgress: (callback) => 
    ipcRenderer.on('download:progress', callback),
  onUpdateAvailable: (callback) => 
    ipcRenderer.on('update:available', callback)
});
