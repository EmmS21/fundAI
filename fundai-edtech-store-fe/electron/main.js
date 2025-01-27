const { app, BrowserWindow } = require('electron');
const path = require('path');
const isDev = process.env.NODE_ENV === 'development';

let mainWindow;

const createWindow = () => {
  try {
    mainWindow = new BrowserWindow({
      width: 1200,
      height: 800,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        preload: path.join(__dirname, 'preload.js')
      },
      show: false, // Don't show until ready
      backgroundColor: '#ffffff'
    });

    // Handle window ready-to-show
    mainWindow.once('ready-to-show', () => {
      mainWindow.show();
    });

    // Load the app
    if (isDev) {
      mainWindow.loadURL('http://localhost:5173');
      mainWindow.webContents.openDevTools();
    } else {
      mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
    }

    // Handle window closed
    mainWindow.on('closed', () => {
      mainWindow = null;
    });

  } catch (error) {
    console.error('Failed to create window:', error);
    app.quit();
  }
};

// App lifecycle handlers
app.whenReady().then(createWindow).catch(error => {
  console.error('Failed to initialize app:', error);
  app.quit();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (!mainWindow) {
    createWindow();
  }
});

// Handle any uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
  app.quit();
});
