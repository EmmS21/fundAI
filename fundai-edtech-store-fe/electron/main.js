const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const isDev = process.env.NODE_ENV === 'development';
const Store = require('electron-store');

/** @typedef {import('./types').WindowState} WindowState */

class WindowStateManager {
    /** @type {import('electron-store')} */
    store;
    /** @type {WindowState} */
    state;

    constructor(defaultWidth, defaultHeight) {
        const defaultState = {
            width: defaultWidth,
            height: defaultHeight,
            x: undefined,
            y: undefined,
            isMaximized: false
        };

        this.store = new Store({
            name: 'window-state',
            defaults: {
                windowState: defaultState
            }
        });

        this.state = this.store.get('windowState');
    }

    get savedState() {
        return this.state;
    }

    /**
     * @param {import('electron').BrowserWindow} window
     */
    saveState(window) {
        // ... rest of the code
    }
}

module.exports = { WindowStateManager };

let mainWindow;

const createWindow = () => {
  try {
    const stateManager = new WindowStateManager(1200, 800);
    const windowState = stateManager.savedState;

    mainWindow = new BrowserWindow({
      width: windowState.width,
      height: windowState.height,
      x: windowState.x,
      y: windowState.y,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        preload: path.join(__dirname, 'preload.js')
      },
      show: false,
      backgroundColor: '#ffffff'
    });

    if (windowState.isMaximized) {
      mainWindow.maximize();
    }

    mainWindow.once('ready-to-show', () => {
      mainWindow.show();
    });

    if (isDev) {
      mainWindow.loadURL('http://localhost:5173');
      mainWindow.webContents.openDevTools();
    } else {
      mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
    }

    mainWindow.on('close', () => {
      stateManager.saveState(mainWindow);
    });

    mainWindow.on('closed', () => {
      mainWindow = null;
    });

    // Setup all handlers
    setupAuthHandlers();
  } catch (error) {
    console.error('Failed to create window:', error);
    app.quit();
  }
};

const setupAuthHandlers = () => {
  ipcMain.handle('auth:adminLogin', async (_, { email, password }) => {
    try {
      // Log the request details (but mask the password)
      console.log('Attempting admin login with:', {
        url: `${VAULT_URL}/api/v1/admin/login`,
        email: email,
        password: password, // Show only last 4 chars
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      });

      const response = await fetch(`${VAULT_URL}/api/v1/admin/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ email, password })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Store credentials along with token
      store.set('auth', {
        email,           // Store admin email
        password,        // Store admin password
        token: data.access_token,
        tokenType: 'Bearer',
        expiresAt: Date.now() + (24 * 60 * 60 * 1000),
        isAdmin: true
      });
      
      return { 
        success: true, 
        isAdmin: true
      };
    } catch (error) {
      console.error('Admin login failed:', error);
      return { 
        success: false, 
        error: error.message
      };
    }
  });

  ipcMain.handle('auth:checkToken', () => {
    const auth = store.get('auth');
    if (!auth) return { isValid: false };
    
    return {
      isValid: auth.expiresAt > Date.now(),
      isAdmin: true
    };
  });

  ipcMain.handle('auth:checkAdmin', () => {
    const auth = store.get('auth');
    return auth?.isAdmin || false;
  });

  ipcMain.handle('auth:clearAuth', () => {
    console.log('Clearing auth...');
    store.delete('auth');
    return true;
  });

  ipcMain.handle('user:get-all', async () => {
    try {
      const auth = store.get('auth');
      if (!auth || !auth.token) {
        throw new Error('Not authenticated');
      }

      let response = await fetch(`${VAULT_URL}/api/v1/admin/users`, {
        headers: {
          'Authorization': `Bearer ${auth.token}`,
          'Accept': 'application/json'
        }
      });

      // If token is invalid (403), try to get new token
      if (response.status === 403) {
        console.log('Token invalid, getting new token...');
        
        const loginResponse = await fetch(`${VAULT_URL}/api/v1/admin/login`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify({
            email: auth.email,
            password: auth.password
          })
        });

        if (!loginResponse.ok) {
          console.error('Failed to refresh token:', {
            status: loginResponse.status,
            statusText: loginResponse.statusText
          });
          throw new Error('Failed to refresh admin token');
        }

        const newAuth = await loginResponse.json();
        
        // Update stored token
        store.set('auth', {
          ...auth,
          token: newAuth.access_token
        });

        // Retry request with new token
        response = await fetch(`${VAULT_URL}/api/v1/admin/users`, {
          headers: {
            'Authorization': `Bearer ${newAuth.access_token}`,
            'Accept': 'application/json'
          }
        });
      }

      if (!response.ok) {
        const errorData = await response.text();
        console.error('API Error Response:', {
          status: response.status,
          statusText: response.statusText,
          body: errorData
        });
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      
      if (data && data.users && Array.isArray(data.users)) {
        const transformedUsers = data.users.map(user => ({
          id: user[0],
          email: user[1],
          // Skip index 2 as it's the password
          full_name: user[3],
          address: user[4],
          city: user[5],
          country: user[6],
          created_at: user[7],
          // Default values for status fields
          status: 'inactive',
          subscription_status: 'inactive'
        }));
        return transformedUsers;
      }

      return [];
    } catch (error) {
      console.error('Failed to get users:', {
        message: error.message,
        stack: error.stack,
        type: error.constructor.name
      });
      throw error;
    }
  });

  ipcMain.handle('user:update-status', async (_, userId, status) => {
    return makeAdminRequest(`/api/v1/admin/users/${userId}/${status}`, {
      method: 'POST'
    });
  });

  ipcMain.handle('user:delete', async (_, userId) => {
    return makeAdminRequest(`/api/v1/admin/users/${userId}`, {
      method: 'DELETE'
    });
  });
};

// Call this after store initialization
app.whenReady().then(() => {
  createWindow();
}).catch(error => {
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

const HUBSTORE_URL = 'https://fundaihubstore.onrender.com';
const VAULT_URL = 'https://fundai.onrender.com';

// Add IPC handlers
ipcMain.handle('store:getApps', async () => {
  try {
    console.log('Hub', HUBSTORE_URL);
    const url = `${HUBSTORE_URL}/api/content/list`;
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    // Only read the response body once
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Failed to fetch apps:', error);
    throw error;
  }
});

// Define schema for type safety and structure
const schema = {
  auth: {
    type: 'object',
    properties: {
      token: { type: 'string' },
      tokenType: { type: 'string' },
      expiresAt: { type: 'number' }
    }
  }
};

// Initialize store once
const store = new Store({ 
  schema,
  name: 'auth-store', // This creates a separate auth-store.json file
  encryptionKey: 'your-encryption-key' // For securing sensitive data
});
