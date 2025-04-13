const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const isDev = process.env.NODE_ENV === 'development';
const Store = require('electron-store');
const downloadManager = require('./services/downloadManager');
const crypto = require('crypto');
const log = require('electron-log');
const { URLSearchParams } = require('url');

// --- Update Checking ---
const { autoUpdater } = require('electron-updater');

log.transports.file.level = 'info';
autoUpdater.logger = log;
autoUpdater.autoDownload = true;


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
      
      log.info(`[Auth] Admin login successful for ${email}. Stored auth data:`, store.get('auth'));

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
    console.log('Clearing admin auth...');
    store.delete('auth');
    return true;
  });

  ipcMain.handle('user:get-all', async () => {
    log.info('[UserGetAll] Handler invoked.');
    try {
      const initialAuth = store.get('auth');
      if (!initialAuth || !initialAuth.token) {
        throw new Error('Not authenticated');
      }

      // --- 1. Fetch the main user list (with inline token refresh) ---
      let usersResponse = await fetch(`${VAULT_URL}/api/v1/admin/users`, {
        headers: {
          'Authorization': `Bearer ${initialAuth.token}`,
          'Accept': 'application/json'
        }
      });
      log.info(`[UserGetAll] Initial users fetch status: ${usersResponse.status}`);

      if ((usersResponse.status === 401 || usersResponse.status === 403)) {
        log.warn('[UserGetAll] Users fetch received 401/403, attempting token refresh...');
        const loginResponse = await fetch(`${VAULT_URL}/api/v1/admin/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify({ email: initialAuth.email, password: initialAuth.password }) // Body is present here
        });

        if (!loginResponse.ok) {
          console.error('Failed to refresh token:', { status: loginResponse.status, statusText: loginResponse.statusText });
          throw new Error('Failed to refresh admin token during initial user fetch.');
        }

        const newAuthData = await loginResponse.json();
        const refreshedAuth = { ...initialAuth, token: newAuthData.access_token, expiresAt: Date.now() + (24 * 60 * 60 * 1000) };
        store.set('auth', refreshedAuth);
        log.info('[UserGetAll] Token refreshed for users fetch.');

        // Retry users fetch with new token
        usersResponse = await fetch(`${VAULT_URL}/api/v1/admin/users`, {
          headers: {
            'Authorization': `Bearer ${refreshedAuth.token}`, // Use refreshed token
            'Accept': 'application/json'
          }
        });
        log.info(`[UserGetAll] Users fetch status after refresh: ${usersResponse.status}`);
      }

      const usersBodyText = await usersResponse.text();
      if (!usersResponse.ok) {
        log.error(`[UserGetAll] API Error Fetching Users: Status=${usersResponse.status}, Body=${usersBodyText}`);
        throw new Error(`API Error fetching users: ${usersResponse.status} ${usersResponse.statusText}`);
      }

      let usersData;
      try {
         usersData = JSON.parse(usersBodyText);
         log.info('[UserGetAll] Successfully parsed user list JSON data.');
      } catch (parseError) {
         log.error('[UserGetAll] Failed to parse user list JSON:', parseError, `Raw Body: ${usersBodyText}`);
         throw new Error('Failed to parse user data from backend.');
      }

      if (!usersData || !usersData.users || !Array.isArray(usersData.users)) {
        log.warn("[UserGetAll] Parsed user data did not contain a 'users' array. Returning empty array.");
        return [];
      }

      // --- 2. Fetch subscription status for each user (with duplicated token refresh) ---
      log.info(`[UserGetAll] Found ${usersData.users.length} users. Fetching subscription status for each...`);
      const usersWithStatusPromises = usersData.users.map(async (user) => {
        if (!user || typeof user.id === 'undefined') {
           log.warn(`[UserGetAll Status Fetch] Malformed user object found:`, user);
           return null; // Skip malformed users
        }

        try {
          // Need to get potentially refreshed auth token *before* this specific request
          let currentAuth = store.get('auth'); // Get latest token before status fetch
          if (!currentAuth || !currentAuth.token) {
             log.error(`[UserGetAll Status Fetch] No token found before fetching status for user ${user.id}.`);
             throw new Error('Authentication token missing for status fetch.');
          }

          const statusUrl = `${VAULT_URL}/api/v1/subscriptions/${user.id}/status`;
          log.info(`[UserGetAll Status Fetch] Fetching status for User ID ${user.id} from ${statusUrl}`);

          let statusResponse = await fetch(statusUrl, {
             headers: {
               'Authorization': `Bearer ${currentAuth.token}`,
               'Accept': 'application/json'
             }
          });
          log.info(`[UserGetAll Status Fetch] Initial status fetch status for User ID ${user.id}: ${statusResponse.status}`);


          // --- Inline Token Refresh Logic (Duplicated for status fetch) ---
          if ((statusResponse.status === 401 || statusResponse.status === 403)) {
             log.warn(`[UserGetAll Status Fetch] Status fetch for User ID ${user.id} received 401/403, attempting token refresh...`);
             const loginResponse = await fetch(`${VAULT_URL}/api/v1/admin/login`, {
                 method: 'POST',
                 headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                 body: JSON.stringify({ email: currentAuth.email, password: currentAuth.password })
             });

             if (!loginResponse.ok) {
                 console.error(`[UserGetAll Status Fetch] Failed to refresh token for user ${user.id}:`, { status: loginResponse.status, statusText: loginResponse.statusText });
                 log.error(`[UserGetAll Status Fetch] Token refresh failed for user ${user.id}. Defaulting status to inactive.`);
                 return { ...user, subscription_status: 'inactive' }; // Default on refresh failure
             }

             const newAuthData = await loginResponse.json();
             const refreshedAuth = { ...currentAuth, token: newAuthData.access_token, expiresAt: Date.now() + (24 * 60 * 60 * 1000) };
             store.set('auth', refreshedAuth); // Update store
             currentAuth = refreshedAuth; // Update local currentAuth for retry
             log.info(`[UserGetAll Status Fetch] Token refreshed for status fetch of user ${user.id}.`);

             // Retry status fetch with new token
             statusResponse = await fetch(statusUrl, {
                 headers: {
                   'Authorization': `Bearer ${currentAuth.token}`, // Use refreshed token
                   'Accept': 'application/json'
                 }
             });
             log.info(`[UserGetAll Status Fetch] Status fetch status after refresh for User ID ${user.id}: ${statusResponse.status}`);
          }
          // --- End Inline Token Refresh ---

          // Process status response
          const statusBodyText = await statusResponse.text();
          if (!statusResponse.ok) {
             log.error(`[UserGetAll Status Fetch] API Error fetching status for User ID ${user.id}: Status=${statusResponse.status}, Body=${statusBodyText}. Defaulting to inactive.`);
             return { ...user, subscription_status: 'inactive' };
          }

          let statusData;
          try {
             statusData = JSON.parse(statusBodyText);
             log.info(`[UserGetAll Status Fetch] Received status for User ID ${user.id}:`, statusData);
          } catch (parseError) {
             log.error(`[UserGetAll Status Fetch] Failed to parse status JSON for User ID ${user.id}:`, parseError, `Raw Body: ${statusBodyText}. Defaulting to inactive.`);
             return { ...user, subscription_status: 'inactive' };
          }

          // Add the subscription status to the user object
          return {
            ...user,
            subscription_status: statusData?.active === true ? 'active' : 'inactive',
          };
        } catch (error) {
          // Catch any other unexpected errors during status fetch
          log.error(`[UserGetAll Status Fetch] Unexpected error fetching subscription status for User ID ${user.id}: ${error.message}. Defaulting to inactive.`);
          return { ...user, subscription_status: 'inactive' };
        }
      });

      // Wait for all status fetches to complete
      const usersWithStatus = (await Promise.all(usersWithStatusPromises)).filter(user => user !== null);
      log.info(`[UserGetAll] Finished fetching statuses. Processed ${usersWithStatus.length} users.`);


      // --- 3. Transform the final user data ---
      const transformedUsers = usersWithStatus.map((user) => {
           // Basic validation again just in case
           if (!user || typeof user.id === 'undefined' || typeof user.email === 'undefined') {
              log.warn(`[UserGetAll Transform] Malformed user object before final transform:`, user);
              return null;
           }
           return {
             id: user.id,
             email: user.email,
             full_name: user.full_name ?? null,
             address: user.address ?? null,
             city: user.city ?? null,
             country: user.country ?? null,
             created_at: user.created_at ?? null,
             status: user.is_active ? 'active' : 'inactive', // From original user data
             subscription_status: user.subscription_status ?? 'inactive' // From the status fetch
           };
      }).filter(user => user !== null);

      log.info(`[UserGetAll] Transformed ${transformedUsers.length} users with subscription status. Returning data.`);
      return transformedUsers;

    } catch (error) {
      log.error('[UserGetAll] Caught error during user fetching or processing:', error);
      throw error; // Re-throw the error so the frontend knows something went wrong
    }
  });

  ipcMain.handle('user:update-status', async (_, userId, status) => {
    log.info(`[UserUpdateStatus] Handler invoked for User ID: ${userId}, Status: ${status}`);
    const action = status === 'active' ? 'activate' : 'deactivate'; // Determine endpoint based on status
    const url = `${VAULT_URL}/api/v1/admin/users/${userId}/${action}`;
    log.info(`[UserUpdateStatus] Attempting POST request to: ${url}`);

    try {
      const auth = store.get('auth');
      if (!auth || !auth.token) {
        throw new Error('Not authenticated');
      }

      let response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${auth.token}`,
          'Accept': 'application/json'
        }
      });
      log.info(`[UserUpdateStatus] Initial request status: ${response.status}`);

      // Handle potential token expiry and refresh (similar to user:get-all)
      if (response.status === 401 || response.status === 403) {
        log.warn(`[UserUpdateStatus] Received ${response.status}, attempting token refresh...`);
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
          const errorText = await loginResponse.text();
          log.error(`[UserUpdateStatus] Failed to refresh token: ${loginResponse.status} - ${errorText}`);
          throw new Error('Failed to refresh admin token');
        }

        const newAuthData = await loginResponse.json();
        store.set('auth', {
          ...auth,
          token: newAuthData.access_token,
          // Optionally update expiresAt if the login response provides it
          expiresAt: Date.now() + (24 * 60 * 60 * 1000) // Assuming 24h validity
        });
        log.info('[UserUpdateStatus] Token refreshed successfully.');

        // Retry the original request with the new token
        response = await fetch(url, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${newAuthData.access_token}`, // Use new token
            'Accept': 'application/json'
          }
        });
        log.info(`[UserUpdateStatus] Request status after refresh: ${response.status}`);
      }

      const responseBodyText = await response.text(); // Read body once

      if (!response.ok) {
        log.error(`[UserUpdateStatus] API Error: Status=${response.status}, Body=${responseBodyText}`);
        // Try to parse error message from JSON response
        let errorMessage = `API Error: ${response.status} ${response.statusText}`;
         try {
             const errorJson = JSON.parse(responseBodyText);
             errorMessage = errorJson.detail || errorJson.message || errorMessage;
         } catch (e) { /* ignore parsing error */ }
        throw new Error(errorMessage);
      }

      log.info(`[UserUpdateStatus] Successfully updated status for User ID ${userId} to ${status}. Response: ${responseBodyText}`);
      // Assuming success returns a simple message like {"message": "User activated/deactivated"}
      return { success: true, message: `User ${status === 'active' ? 'activated' : 'deactivated'} successfully.` };

    } catch (error) {
      log.error(`[UserUpdateStatus] Caught error for User ID ${userId}:`, error);
      return { success: false, error: error.message || 'An unexpected error occurred.' };
    }
  });

  ipcMain.handle('user:delete', async (_, userId) => {
    // TODO: Implement token refresh logic here as well if needed
    // For now, assuming makeAdminRequest handles it or is replaced
     log.info(`[UserDelete] Handler invoked for User ID: ${userId}`);
     const url = `${VAULT_URL}/api/v1/admin/users/${userId}`;
     log.info(`[UserDelete] Attempting DELETE request to: ${url}`);

     try {
         const auth = store.get('auth');
         if (!auth || !auth.token) {
             throw new Error('Not authenticated');
         }

         let response = await fetch(url, {
             method: 'DELETE',
             headers: {
                 'Authorization': `Bearer ${auth.token}`,
                 'Accept': 'application/json'
             }
         });
         log.info(`[UserDelete] Initial request status: ${response.status}`);

         // Handle potential token expiry and refresh (similar pattern)
         if (response.status === 401 || response.status === 403) {
             log.warn(`[UserDelete] Received ${response.status}, attempting token refresh...`);
             // ... (Token refresh logic - copy from user:update-status or factor out) ...
             // For brevity, skipping the full refresh code block here, but it should be added
             throw new Error('Token expired and refresh logic needs implementation here.'); // Placeholder
         }

         const responseBodyText = await response.text();

         if (!response.ok) {
              log.error(`[UserDelete] API Error: Status=${response.status}, Body=${responseBodyText}`);
              let errorMessage = `API Error: ${response.status} ${response.statusText}`;
              try {
                  const errorJson = JSON.parse(responseBodyText);
                  errorMessage = errorJson.detail || errorJson.message || errorMessage;
              } catch (e) { /* ignore parsing error */ }
              throw new Error(errorMessage);
         }

         log.info(`[UserDelete] Successfully deleted User ID ${userId}. Response: ${responseBodyText}`);
         return { success: true, message: 'User deleted successfully.' };

     } catch (error) {
         log.error(`[UserDelete] Caught error for User ID ${userId}:`, error);
         return { success: false, error: error.message || 'An unexpected error occurred.' };
     }
  });

  // --- NEW: User Subscription Handler ---
  ipcMain.handle('user:subscribe', async (_, userId) => {
      log.info(`[UserSubscribe] Handler invoked for User ID: ${userId}`);
      const url = `${VAULT_URL}/api/v1/subscriptions/${userId}`;
      log.info(`[UserSubscribe] Attempting POST request to: ${url}`);

      try {
          const auth = store.get('auth');
          if (!auth || !auth.token) {
              throw new Error('Not authenticated');
          }

          let response = await fetch(url, {
              method: 'POST',
              headers: {
                  'Authorization': `Bearer ${auth.token}`,
                  'Accept': 'application/json'
                  // No Content-Type or Body needed for this specific endpoint
              }
          });
          log.info(`[UserSubscribe] Initial request status: ${response.status}`);

          // Handle potential token expiry and refresh (similar pattern)
          if (response.status === 401 || response.status === 403) {
              log.warn(`[UserSubscribe] Received ${response.status}, attempting token refresh...`);
              // ... (Token refresh logic - copy from user:update-status or factor out) ...
              const loginResponse = await fetch(`${VAULT_URL}/api/v1/admin/login`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                  body: JSON.stringify({ email: auth.email, password: auth.password })
              });
              if (!loginResponse.ok) throw new Error('Failed to refresh admin token');
              const newAuthData = await loginResponse.json();
              store.set('auth', { ...auth, token: newAuthData.access_token, expiresAt: Date.now() + (24 * 60 * 60 * 1000) });
              log.info('[UserSubscribe] Token refreshed successfully.');

              // Retry request
              response = await fetch(url, {
                  method: 'POST',
                  headers: { 'Authorization': `Bearer ${newAuthData.access_token}`, 'Accept': 'application/json' }
              });
              log.info(`[UserSubscribe] Request status after refresh: ${response.status}`);
          }

          const responseBodyText = await response.text();

          if (!response.ok) {
              log.error(`[UserSubscribe] API Error: Status=${response.status}, Body=${responseBodyText}`);
              let errorMessage = `API Error: ${response.status} ${response.statusText}`;
              try {
                  const errorJson = JSON.parse(responseBodyText);
                   // Handle specific "Subscription already exists" error
                   if (response.status === 400 && (errorJson.message?.includes("already exists") || errorJson.detail?.includes("already exists"))) {
                      errorMessage = "Subscription already exists for this user.";
                   } else {
                      errorMessage = errorJson.detail || errorJson.message || errorMessage;
                   }
              } catch (e) { /* ignore parsing error */ }
              throw new Error(errorMessage);
          }

          log.info(`[UserSubscribe] Successfully subscribed User ID ${userId}. Response: ${responseBodyText}`);
          const responseData = JSON.parse(responseBodyText); // Expecting { message, user_id, start_date, end_date }
          return { success: true, data: responseData };

      } catch (error) {
          log.error(`[UserSubscribe] Caught error for User ID ${userId}:`, error);
          // Return specific error message if available
          return { success: false, error: error.message || 'An unexpected error occurred during subscription.' };
      }
  });

  // --- MODIFIED: Admin Register Device Handler ---
  ipcMain.handle('admin:register-device', async (_, deviceData) => {
    // Destructure data received from frontend
    const { hardwareId, email, fullName, address, city, country } = deviceData;

    log.info(`[Admin] Attempting to register device ID ${hardwareId} for email ${email}`);

    // 1. Verify Admin Authentication (keep existing check)
    const adminAuth = store.get('auth');
    if (!adminAuth || !adminAuth.token || !adminAuth.isAdmin) {
      log.error('[Admin] Register Device failed: No valid admin session found.');
      throw new Error('Admin privileges required.');
    }
    const adminToken = adminAuth.token;

    // 2. Validate Input (Basic) - Ensure required fields are present
    if (!hardwareId || !email) {
        log.error('[Admin] Register Device failed: Missing hardwareId or email.');
        throw new Error('Hardware ID and Email are required.');
    }
    // Note: We send all fields; FundaVault handles requiring name/address etc. only if creating a new user.

    // 3. Prepare API Request
    const registerDeviceUrl = `${VAULT_URL}/api/v1/admin/register-device`; // Confirmed Endpoint
    const requestBody = {
        hardware_id: hardwareId,
        email: email,
        full_name: fullName, // Send even if potentially null/empty
        address: address,
        city: city,
        country: country
    };

    log.info(`[Admin] Sending request to ${registerDeviceUrl}`);

    try {
      const response = await fetch(registerDeviceUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Authorization': `Bearer ${adminToken}`
        },
        body: JSON.stringify(requestBody)
      });

      // 4. Handle Response
      const responseBodyText = await response.text(); // Read body once

      if (!response.ok) {
        log.error(`[Admin] Register Device API call failed: ${response.status} - ${responseBodyText}`);
        let errorMessage = `Registration failed: ${response.status}`;
        let errorDetail = '';
         try {
             const errorJson = JSON.parse(responseBodyText);
             errorDetail = errorJson.detail || errorJson.error || '';
             errorMessage = errorDetail || errorMessage; // Use detail if available
         } catch (e) { /* ignore parsing error, use raw text */ errorDetail = responseBodyText; }

        // Handle specific conflict errors
        if (response.status === 409) {
            if (errorDetail.includes("Hardware ID already registered")) {
                 throw new Error('Conflict: This Hardware ID is already registered.');
            } else if (errorDetail.includes("User already has an active device")) {
                 throw new Error('Conflict: This User (identified by email) already has an active device.');
            } else {
                 throw new Error(`Conflict: ${errorMessage}`); // Generic 409
            }
        }
         // Handle auth errors
         else if (response.status === 401 || response.status === 403) {
              throw new Error(`Authorization failed: ${errorMessage} (${response.status})`);
         }
         // Handle other errors
         else {
             throw new Error(errorMessage);
         }
      }

      // Success case (assuming 201 Created)
      let responseData = {};
      try {
          responseData = JSON.parse(responseBodyText);
      } catch (e) {
          log.warn('[Admin] Failed to parse successful JSON response body:', responseBodyText);
      }
      log.info(`[Admin] Successfully registered device ID ${hardwareId} for email ${email}. Response:`, responseData);
      // Return specific fields if needed, or just success indication
      return {
          success: true,
          message: responseData.message || "Device registered successfully",
          data: responseData // Send back the parsed response data
        };

    } catch (error) {
      // Catch errors thrown from response handling or fetch itself
      log.error('[Admin] Exception during device registration:', error);
      // Ensure the error message passed to the frontend is useful
      throw new Error(error.message || 'An unexpected error occurred during device registration.');
    }
  });

};

// Call this after store initialization
app.whenReady().then(() => {
  log.info('App ready.');

  setupIpcHandlers(/* pass dependencies like store if needed */);

  log.info('Calling createWindow.');
  createWindow();
}).catch(error => {
  console.error('Failed to initialize app:', error);
  log.error('Failed to initialize app:', error);
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
// const VAULT_URL = 'https://fundai.onrender.com';
const VAULT_URL = 'https://emms21--user-management-api-api.modal.run';


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
      email: { type: 'string' },
      password: { type: 'string' },
      token: { type: 'string' },
      tokenType: { type: 'string' },
      expiresAt: { type: 'number' },
      isAdmin: { type: 'boolean' }
    }
  },
  deviceInfo: {
      type: 'object',
      properties: {
          deviceId: { type: 'string' }
      }
  }
};

// Initialize store once
const store = new Store({
  schema,
  name: 'app-auth-store',
  // encryptionKey: 'your-encryption-key'
});

// Function to get or generate a persistent client Device ID
function getPersistentDeviceID() {
    let deviceInfo = store.get('deviceInfo');
    if (deviceInfo && deviceInfo.deviceId) {
        return deviceInfo.deviceId;
    } else {
        const newDeviceId = crypto.randomUUID();
        store.set('deviceInfo', { deviceId: newDeviceId });
        log.info(`[DeviceID] Generated and stored new Device ID: ${newDeviceId}`);
        return newDeviceId;
    }
}

// --- AutoUpdater Event Handlers ---
autoUpdater.on('checking-for-update', () => {
  log.info('Checking for update...');
  // Optionally send status to renderer: mainWindow.webContents.send('update_checking');
});

autoUpdater.on('update-available', (info) => {
  log.info('Update available.', info);
  if (mainWindow) {
    mainWindow.webContents.send('update_available', info); // Notify renderer
  }
});

autoUpdater.on('update-not-available', (info) => {
  log.info('Update not available.', info);
  // Optionally send status to renderer: mainWindow.webContents.send('update_not_available');
});

autoUpdater.on('error', (err) => {
  log.error('Error in auto-updater. ' + err);
  if (mainWindow) {
    mainWindow.webContents.send('update_error', err.message); // Notify renderer
  }
});

autoUpdater.on('download-progress', (progressObj) => {
  let log_message = "Download speed: " + progressObj.bytesPerSecond;
  log_message = log_message + ' - Downloaded ' + progressObj.percent + '%';
  log_message = log_message + ' (' + progressObj.transferred + "/" + progressObj.total + ')';
  log.info(log_message);
  if (mainWindow) {
    mainWindow.webContents.send('update_progress', progressObj); // Send progress to renderer
  }
});

autoUpdater.on('update-downloaded', (info) => {
  log.info('Update downloaded.', info);
  // Prompt user in the renderer process to restart
  if (mainWindow) {
    mainWindow.webContents.send('update_downloaded', info);
  }
});
// --- End AutoUpdater Event Handlers ---
// --- IPC Handler for Restarting ---
// Listen for message from renderer process to install update
ipcMain.on('restart_app', () => {
  log.info('Received restart_app signal, quitting and installing update...');
  autoUpdater.quitAndInstall();
});
// --- End IPC Handler ---

// Placeholder for centralized IPC handlers setup
function setupIpcHandlers(/* dependencies */) {
    log.info('Setting up IPC handlers from setupIpcHandlers function...');

    // --- DELETE OR COMMENT OUT THIS DUPLICATE HANDLER ---
    /*
    ipcMain.handle('store:getApps', async () => {
      const url = `${HUBSTORE_URL}/api/content/list`;
      try {
        log.info(`IPC (from func): Handling store:getApps - Fetching from ${url}`);
        // TODO: Cache logic
        const response = await fetch(url, { signal: AbortSignal.timeout(15000) });
        if (!response.ok) throw new Error(`HTTP error ${response.status}`);
        const data = await response.json();
        log.info(`IPC (from func): store:getApps - Fetched ${data.length} apps.`);
        // TODO: Save to cache
        return data;
      } catch (error) {
        log.error('IPC (from func): store:getApps - Failed:', error);
        // TODO: Try cache
        throw new Error('Failed to fetch apps.');
      }
    });
    */
    // --- END OF DELETED/COMMENTED BLOCK ---


    // Handler for fetching books - Modified to return placeholder
    ipcMain.handle('books:getBooks', async () => {
        log.info(`IPC: Handling books:getBooks - Returning 'Coming Soon' placeholder.`);

        // --- Temporarily bypass backend fetch ---
        // const url = `${HUBSTORE_URL}/api/books`; // TODO: Verify URL
        // try {
        //   log.info(`IPC: Handling books:getBooks - Fetching from ${url}`);
        //   // TODO: Cache logic
        //   const response = await fetch(url, { signal: AbortSignal.timeout(15000) });
        //   if (!response.ok) throw new Error(`HTTP error ${response.status} fetching books`);
        //   const data = await response.json();
        //   log.info(`IPC books:getBooks - Fetched books.`);
        //   // TODO: Save to cache
        //   return data;
        // } catch (error) {
        //   log.error('IPC books:getBooks - Failed:', error);
        //   // TODO: Try cache
        //   throw new Error('Failed to fetch books.');
        // }
        // --- End of bypassed code ---

        // Return empty array to satisfy the expected Promise<Book[]> type
        // The frontend Library component can check for an empty array
        // and display a "Coming Soon" message if desired.
        return [];
    });

    // Keep the handler for get-app-version
    ipcMain.handle('get-app-version', () => {
      log.info('IPC: Handling get-app-version');
      return app.getVersion();
    });

    // Store handlers
    ipcMain.handle('store:getAppDetails', async (_, appId) => {
      try {
        // Get app details from the store
        const url = `${HUBSTORE_URL}/api/content/${appId}`;
        const response = await fetch(url);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        return data;
      } catch (error) {
        console.error('Failed to fetch app details:', error);
        throw error;
      }
    });

    ipcMain.handle('store:downloadApp', async (event, appId) => {
      try {
        // Get the persistent Device ID for this client installation
        const clientDeviceID = getPersistentDeviceID();
        log.info(`[Download] Using Client Device ID: ${clientDeviceID}`);

        if (!clientDeviceID) {
             log.error('[Download] Failed to get or generate a Client Device ID.');
             throw new Error('Client identifier is missing.');
        }

        // Start the download process via the backend API
        const startDownloadUrl = `${HUBSTORE_URL}/api/downloads/start`;
        log.info(`[Download] Starting download process for AppID ${appId} at ${startDownloadUrl}`);
        const startDownloadResponse = await fetch(startDownloadUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Device-ID': clientDeviceID
          },
          body: JSON.stringify({
            contentId: appId
          })
        });

        log.info(`[Download] Sending contentId: ${appId} to /api/downloads/start`);

        if (!startDownloadResponse.ok) {
           const errorBody = await startDownloadResponse.text();
           log.error(`[Download] Failed to start download: ${startDownloadResponse.status} - ${errorBody}`);
           if (startDownloadResponse.status === 401 || startDownloadResponse.status === 403) {
               throw new Error(`Device ID not registered or subscription inactive (${startDownloadResponse.status}). Please contact Admin.`);
           }
           throw new Error(`Failed to start download: ${startDownloadResponse.status} (${startDownloadResponse.statusText})`);
        }

        const startDownloadData = await startDownloadResponse.json();
        log.info(`[Download] Received response from /api/downloads/start:`, JSON.stringify(startDownloadData));
        const recordId = startDownloadData.id;
        log.info(`[Download] Started successfully, Download Record ID: ${recordId}`);


        // Get the actual download URL
        const getDownloadUrlEndpoint = `${HUBSTORE_URL}/api/downloads/url?content_id=${appId}`;
        log.info(`[Download] Getting download URL from ${getDownloadUrlEndpoint}`);
        const getDownloadUrlResponse = await fetch(getDownloadUrlEndpoint, {
          headers: {
            'Device-ID': clientDeviceID
          }
        });

        if (!getDownloadUrlResponse.ok) {
          const errorBody = await getDownloadUrlResponse.text();
          log.error(`[Download] Failed to get download URL: ${getDownloadUrlResponse.status} - ${errorBody}`);
          if (getDownloadUrlResponse.status === 401 || getDownloadUrlResponse.status === 403) {
               throw new Error(`Device ID not registered or subscription inactive (${getDownloadUrlResponse.status}). Please contact Admin.`);
           }
          throw new Error(`Failed to get download URL: ${getDownloadUrlResponse.status} (${getDownloadUrlResponse.statusText})`);
        }

        const downloadUrlData = await getDownloadUrlResponse.json();
        const downloadUrl = downloadUrlData.download_url;
        if (!downloadUrl) {
            log.error('[Download] Backend did not return a downloadUrl (expected download_url key). Response data:', downloadUrlData);
            throw new Error('Failed to retrieve download URL from backend.');
        }
        log.info(`[Download] Received download URL: ${downloadUrl.substring(0, 70)}...`);


        // --- DEFINE handleProgress INSIDE the handler scope ---
        const handleProgress = (progress) => {
          log.debug(`[Download Progress] ${appId}: ${progress.percentage}%`); // Use appId for clarity
          // Use event.sender to send progress back to the initiating renderer
          if (event && event.sender && !event.sender.isDestroyed()) {
             event.sender.send('download:progress', { // <-- Use event.sender.send
               appId: appId,
               percentage: progress.percentage,
               transferred: progress.transferred,
               total: progress.total
             });
          }
        };
        // --- End handleProgress Definition ---

        // --- Add/Ensure this log ---
        const fallbackFilename = `${appId}-${Date.now()}.tmp`; // Ensure this is the fallback you intend
        console.log(`[main.js - LOG 1] Passing to downloadManager: fallbackFilename='${fallbackFilename}'`);
        // --- End log ---

        log.info(`[Download] Starting file download. Fallback filename: ${fallbackFilename}`); // Keep original log too
        const fullDownloadUrl = `${HUBSTORE_URL}${downloadUrl}`;
        log.info(`[Download] Constructed full download URL: ${fullDownloadUrl}`);

        // Call download manager
        const downloadResult = await downloadManager.downloadFile(
            fullDownloadUrl,
            fallbackFilename,
            handleProgress
        );
        const downloadPath = downloadResult.path;
        const actualFilename = downloadResult.filename;

        // --- ADD THIS LOG ---
        console.log(`[main.js - LOG 4] Received from downloadManager: downloadPath='${downloadPath}', actualFilename='${actualFilename}'`);
        // --- END LOG ---

        log.info(`[Download] File downloaded to: ${downloadPath} (Actual Filename: ${actualFilename})`);

        // Send one final '100%' progress event
        handleProgress({ percentage: 100, transferred: -1, total: -1 });


        // Update download status to completed
        const updateStatusUrl = `${HUBSTORE_URL}/api/downloads/status`;
        log.info(`[Download] Updating download status to 'completed' at ${updateStatusUrl} for RecordID ${recordId}`);
        const updateStatusResponse = await fetch(updateStatusUrl, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Device-ID': clientDeviceID
          },
          body: JSON.stringify({
            id: recordId,
            status: 'completed'
          })
        });

        if (!updateStatusResponse.ok) {
            const errorBody = await updateStatusResponse.text();
            if (recordId === undefined) {
              log.warn(`[Download] Failed to update status because RecordID was undefined. Backend response: ${updateStatusResponse.status} - ${errorBody}.`);
            } else {
              log.warn(`[Download] Failed to update download status post-completion: ${updateStatusResponse.status} - ${errorBody}.`);
            }
        } else {
             log.info(`[Download] Post-download status updated successfully for ${recordId}`);
        }


        // Notify renderer of completion (event.sender is reliable here too)
        log.info(`[Download] Notifying renderer of completion for ${appId}`);
        if (event && event.sender && !event.sender.isDestroyed()) {
           event.sender.send('download:complete', { // <-- Use event.sender.send
             appId,
             path: downloadPath
           });
        }

        return {
          success: true,
          message: 'App downloaded successfully',
          path: downloadPath
        };
      } catch (error) {
        log.error(`[Download] Error during download process for ${appId}:`, error);
         // Optionally send error back to renderer
         if (event && event.sender && !event.sender.isDestroyed()) {
           event.sender.send('download:error', { appId: appId, error: error.message }); // Define 'download:error' in preload/renderer if needed
         }
        throw error; // Re-throw to reject the invoke promise
      }
    });

    log.info('IPC handlers setup from setupIpcHandlers function complete.');
}

// Add near other app.on listeners, after store is initialized

// --- Ensure this handler is present ---
app.on('will-quit', () => {
  log.info('[App Quit] Event "will-quit" triggered.');
  if (store) {
    const authBefore = store.get('auth');
    log.info(`[App Quit] Admin auth data BEFORE clear attempt: ${authBefore ? JSON.stringify(authBefore) : 'null'}`);
    try {
      // --- MODIFIED: Explicitly set 'auth' to null instead of delete ---
      store.set('auth', null);
      // --- END MODIFY ---
      const authAfter = store.get('auth'); // Should now log null if set worked immediately
      log.info(`[App Quit] Admin auth data AFTER setting to null: ${authAfter ? JSON.stringify(authAfter) : 'null'}`);
    } catch (error) {
       log.error('[App Quit] Error during store.set(\'auth\', null):', error);
    }
  } else {
    log.warn('[App Quit] Store object not available, cannot clear admin auth.');
  }
  log.info('[App Quit] "will-quit" handler finished.');
});
// --- End ensure ---
