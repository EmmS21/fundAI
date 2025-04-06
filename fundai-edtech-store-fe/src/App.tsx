import React, { useState, useEffect } from 'react';
import Store from './pages/Store';
import Library from './pages/Library';
import { Header } from './components/layout/Header';
import { ThemeProvider } from './context/ThemeContext';
import LoginModal from './components/auth/LoginModal';
import { useAuth } from './hooks/useAuth';
import { UploadModal } from './components/admin/UploadModal';
import UsersModal from './components/admin/UsersModal';

// --- Define interfaces matching electron.d.ts (or import if separate) ---
interface UpdateInfo {
  version: string;
  // Add other fields from electron-updater's UpdateInfo if needed
}
interface ProgressInfo {
  percent: number;
  // Add other fields from electron-updater's ProgressInfo if needed
}
// --- End Interface Definitions ---


export default function App() {
  const [activeTab, setActiveTab] = useState<'apps' | 'library'>('apps');
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showUsersModal, setShowUsersModal] = useState(false);
  const { isAdmin, clearAuth } = useAuth();
  const [headerHeight, setHeaderHeight] = useState(0);

  // --- Auto Updater State ---
  const [updateAvailable, setUpdateAvailable] = useState<UpdateInfo | null>(null); // Keep track if needed for UI
  const [updateDownloaded, setUpdateDownloaded] = useState<UpdateInfo | null>(null);
  const [downloadProgress, setDownloadProgress] = useState<number | null>(null);
  // --- End Auto Updater State ---

  // --- NEW: Online/Offline State ---
  const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);
  const [appVersion, setAppVersion] = useState<string>('');
  // --- End Online/Offline State ---

  // Effect for checking admin status
  useEffect(() => {
    const checkAdminStatus = async () => {
      if (window.electronAPI && typeof window.electronAPI.checkAdmin === 'function') {
        const adminStatus = await window.electronAPI.checkAdmin();
        useAuth.getState().setAuth(null, adminStatus);
      }
    };
    checkAdminStatus();
  }, []);

  // Effect for observing header height
  useEffect(() => {
    const header = document.querySelector('header');
    if (header) {
      const observer = new ResizeObserver(entries => {
        setHeaderHeight(entries[0].contentRect.height);
      });
      observer.observe(header);
      return () => observer.disconnect();
    }
  }, []);

  // --- Setup Listeners & Get Version Effect ---
  useEffect(() => {
    // Log start
    console.log("App component mounted, running main useEffect for listeners and version.");

    // --- Get App Version ---
    const fetchVersion = async () => {
      console.log("Attempting to fetch version...");
      if (window.electronAPI && typeof window.electronAPI.getAppVersion === 'function') {
        console.log("window.electronAPI.getAppVersion found, calling...");
        try {
          const version = await window.electronAPI.getAppVersion();
          console.log("Fetched App Version:", version);
          setAppVersion(version);
        } catch (error) {
          console.error("Failed to fetch app version via IPC:", error);
        }
      } else {
        console.error("window.electronAPI.getAppVersion is not available yet or not defined.");
      }
    };
    fetchVersion();
    // --- End Get App Version ---


    // --- Online/Offline Listeners (Keep This!) ---
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    // --- End Online/Offline Listeners ---


    // --- Auto Updater Listeners (Keep This Block Intact!) ---
    if (window.electronAPI && typeof window.electronAPI.onUpdateAvailable === 'function') {
       console.log("Setting up updater listeners."); // Log listener setup
       const handleUpdateAvailable = (info: UpdateInfo) => {
         console.log('Update Available:', info);
         setUpdateAvailable(info);
         setUpdateDownloaded(null);
         setDownloadProgress(0);
         alert(`Update ${info.version} is available. Downloading...`); // TODO: Replace alert
       };
       const handleUpdateProgress = (progress: ProgressInfo) => {
         console.log('Download Progress:', progress.percent);
         setDownloadProgress(Math.round(progress.percent));
       };
       const handleUpdateDownloaded = (info: UpdateInfo) => {
         console.log('Update Downloaded:', info);
         setUpdateDownloaded(info);
         setDownloadProgress(null);
         // alert(`Update ${info.version} downloaded. Restart to install.`); // TODO: Replace alert
       };
       const handleUpdateError = (errorMessage: string) => {
         console.error('Update Error:', errorMessage);
         setDownloadProgress(null);
         alert(`Update Error: ${errorMessage}`); // TODO: Replace alert
       };
       // Register listeners
       window.electronAPI.onUpdateAvailable(handleUpdateAvailable);
       window.electronAPI.onUpdateProgress(handleUpdateProgress);
       window.electronAPI.onUpdateDownloaded(handleUpdateDownloaded);
       window.electronAPI.onUpdateError(handleUpdateError);
    } else {
        console.log("Electron API (onUpdateAvailable) not available when setting listeners."); // Log if API not ready
    }
    // --- End Auto Updater Listeners ---


    // --- Combined Cleanup (Keep This!) ---
    return () => {
      console.log("Cleaning up App listeners."); // Log cleanup
      // Cleanup online/offline listeners
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      // Cleanup updater listeners
      if (window.electronAPI && window.electronAPI.removeAllUpdateListeners) {
        window.electronAPI.removeAllUpdateListeners();
      }
    };
    // --- End Combined Cleanup ---

  }, []); // Empty dependency array ensures this runs only once on mount
  // --- End COMBINED Setup Effect ---


  // --- Event Handlers ---
  const handleLoginClick = () => {
    setShowLoginModal(true);
  };

  const handleLoginSuccess = () => {
    setShowLoginModal(false);
  };

  const handleSignOut = async () => {
    console.log('triggered sign out');
    try {
      if (window.electronAPI && typeof window.electronAPI.clearAuth === 'function') {
        await window.electronAPI.clearAuth();
        clearAuth(); // This clears Zustand store
        // Re-check admin status after clearing
        const adminStatus = await window.electronAPI.checkAdmin();
        console.log('New admin status after signout:', adminStatus);
      }
    } catch (error) {
      console.error('Error in handleSignOut:', error);
    }
  };

  const handleRestartClick = () => {
    if (window.electronAPI && typeof window.electronAPI.restartApp === 'function') {
      window.electronAPI.restartApp();
    }
  };
  // --- End Event Handlers ---

  return (
    <ThemeProvider>
      <div className="min-h-screen w-full bg-white dark:bg-gray-900 transition-colors overflow-auto">
        <div className="w-full min-h-screen bg-white dark:bg-gray-900 relative">
          {/* Placeholder div that maintains the header's space */}
          <div style={{ height: headerHeight }} />

          <header className="fixed top-0 left-0 right-0 w-full bg-white dark:bg-gray-800 shadow-sm z-50">
            <Header
              activeTab={activeTab}
              onTabChange={setActiveTab}
              onUploadClick={() => setShowUploadModal(true)}
              onUsersClick={() => setShowUsersModal(true)}
            />
          </header>

          <main>
            {activeTab === 'apps' ? <Store /> : <Library />}
          </main>

          {/* --- Online/Offline Indicator Tag --- */}
          <div className={`fixed bottom-4 ${updateDownloaded || (downloadProgress !== null && !updateDownloaded) ? 'left-auto right-4' : 'left-4'} z-[65] px-3 py-1 rounded-full text-xs font-medium shadow-md transition-all duration-300 ${
              isOnline
                ? 'bg-green-100 text-green-800 border border-green-300'
                : 'bg-red-100 text-red-800 border border-red-300'
            }`}
            title={isOnline ? 'Status: Online' : 'Status: Offline'}
          >
            {isOnline ? 'Online' : 'Offline'}
          </div>
          {/* --- End Online/Offline Indicator Tag --- */}

          {/* App Version Tag (ADDITION - Positioned near Online/Offline when it's on the right) */}
          {appVersion && (
             <div className="fixed bottom-4 right-4 mr-[70px] z-[65] px-3 py-1 rounded-full text-xs font-medium shadow-md bg-gray-100 text-gray-800 border border-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:border-gray-600 pointer-events-auto"
                  // Adjust margin-right (mr-[70px]) based on the width of your Online/Offline tag if needed
                  title={`App Version: ${appVersion}`}
             >
               v{appVersion}
             </div>
          )}
          {/* --- End App Version Tag --- */}

          {/* Login/Logout Buttons */}
          {!isAdmin && (
            <button
              onClick={handleLoginClick}
              className="fixed top-4 left-4 z-[60] px-4 py-2 bg-blue-500 text-white rounded-full
                hover:bg-blue-600 transition-colors text-sm font-medium"
            >
              Login
            </button>
          )}

          {isAdmin && (
            <button
              onClick={handleSignOut}
              className="fixed top-4 left-4 z-[60] px-4 py-2 bg-red-500 text-white rounded-full
                hover:bg-red-600 transition-colors text-sm font-medium"
            >
              Sign Out
            </button>
          )}

          {/* Update Download Progress - KEEP THIS */}
          {downloadProgress !== null && !updateDownloaded && (
             <div className="fixed bottom-16 left-4 z-[70] p-3 bg-blue-100 border border-blue-500 text-blue-800 rounded-md shadow-lg text-sm">
               Downloading update: {downloadProgress}%
             </div>
          )}

          {/* Update Downloaded Banner/Button - KEEP THIS */}
          {updateDownloaded && (
            <div className="fixed bottom-16 right-4 z-[70] p-4 bg-green-100 border border-green-600 text-green-800 rounded-md shadow-lg flex items-center gap-4">
              <span>Update {updateDownloaded.version} downloaded.</span>
              <button
                onClick={handleRestartClick}
                className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
              >
                Restart & Install
              </button>
            </div>
          )}

          {/* Modals */}
          {showLoginModal && (
            <div
              className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[80]
                flex items-center justify-center"
              onClick={() => setShowLoginModal(false)}
            >
              <div onClick={e => e.stopPropagation()}>
                <LoginModal
                  onLoginSuccess={handleLoginSuccess}
                  onClose={() => setShowLoginModal(false)}
                />
              </div>
            </div>
          )}

          {showUploadModal && (
            <UploadModal
              onClose={() => setShowUploadModal(false)}
              onUpload={async (formData) => {
                setShowUploadModal(false);
              }}
            />
          )}

          {showUsersModal && (
            <UsersModal
              onClose={() => setShowUsersModal(false)}
            />
          )}
        </div>
      </div>
    </ThemeProvider>
  );
}
