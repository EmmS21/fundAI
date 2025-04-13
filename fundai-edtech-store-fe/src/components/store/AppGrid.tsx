import React, { useState, useEffect } from 'react';
import { App } from '../../types/app';
import { AppCard } from './AppCard';
import { useAppStore } from '../../stores/appStore';
import { useUIStore } from '../../stores/uiStore';

interface AppGridProps {
  apps: App[];
  onAppClick?: (app: App) => void;
}

// Define the structure for progress state
interface DownloadProgress {
  status: 'idle' | 'downloading' | 'complete' | 'error';
  percentage: number;
  error?: string; // Store error message if download fails
}

// Define the type for the progress map
type AppDownloadProgressMap = {
  [appId: string]: DownloadProgress;
};

export const AppGrid: React.FC<AppGridProps> = ({ apps, onAppClick }) => {
  const { loadApps, syncApps, isOffline } = useAppStore();
  const { showSubNoticeOverlay } = useUIStore();
  // State to hold progress for all apps displayed by this grid
  const [downloadProgress, setDownloadProgress] = useState<AppDownloadProgressMap>({});

  useEffect(() => {
    loadApps();
    const syncInterval = setInterval(() => {
        if (!isOffline) {
            syncApps();
        }
    }, 15 * 60 * 1000);

    // --- Setup IPC Listeners ---
    const handleProgress = (data: { appId: string; percentage: number }) => {
      console.log(`[AppGrid] Progress for ${data.appId}: ${data.percentage}%`);
      console.log(`[AppGrid] State BEFORE update for ${data.appId}:`, downloadProgress[data.appId]);
      setDownloadProgress(prev => {
          const newState = {
             ...prev,
             [data.appId]: {
               ...prev[data.appId],
               status: 'downloading',
               percentage: data.percentage,
             }
          };
          console.log(`[AppGrid] State AFTER update for ${data.appId}:`, newState[data.appId]);
          return newState;
       });
    };

    const handleComplete = (data: { appId: string; path: string; error?: string }) => {
      console.log(`[AppGrid] Complete for ${data.appId}`, data.error ? `Error: ${data.error}` : `Path: ${data.path}`);
      console.log(`[AppGrid] State BEFORE complete update for ${data.appId}:`, downloadProgress[data.appId]);
      setDownloadProgress(prev => {
          const newState = {
            ...prev,
            [data.appId]: {
               status: data.error ? 'error' : 'complete',
               percentage: data.error ? prev[data.appId]?.percentage ?? 0 : 100,
               error: data.error,
            }
          };
          return newState;
       });
      // Optionally: reload apps list or update specific app status in main store
      // loadApps();
    };

    // Check if API is available before registering listeners
    if (window.electronAPI?.onDownloadProgress) {
        window.electronAPI.onDownloadProgress(handleProgress);
    }
    if (window.electronAPI?.onDownloadComplete) {
        window.electronAPI.onDownloadComplete(handleComplete);
    }

    // --- Cleanup Listeners ---
    // Returning a function from useEffect performs cleanup on unmount
    return () => {
      // It's generally good practice to remove listeners, but preload.js doesn't
      // currently expose removeListener functions. If you add them, use them here.
      // For now, the listeners attached via preload will persist but shouldn't cause
      // issues unless the component remounts frequently without page reload.
      console.log("[AppGrid] Cleanup: Listeners might persist (no removeListener exposed).");
    };

  }, [loadApps, syncApps, isOffline]); // Dependencies for initial setup

  const handleDownload = async (appId: string) => {
    if (isOffline) {
        console.log('[AppGrid] Download attempt while offline.');
        alert("Cannot start download while offline.");
        return;
    }

    // --- Set initial downloading state ---
    setDownloadProgress(prev => ({
        ...prev,
        [appId]: { status: 'downloading', percentage: 0 }
    }));
    console.log(`[AppGrid] Attempting download for appId: ${appId}`);

    try {
      // The actual download result (path) is handled by onDownloadComplete now
      await window.electronAPI.downloadApp(appId);
      console.log(`[AppGrid] downloadApp IPC invocation successful for ${appId}. Waiting for progress/completion events.`);
      // Don't assume success here, wait for the 'download:complete' event
    } catch (error: any) {
      console.error(`[AppGrid] Error invoking downloadApp for ${appId}:`, error);
       // --- Update state on invocation error ---
       setDownloadProgress(prev => ({
           ...prev,
           [appId]: { status: 'error', percentage: 0, error: error.message }
       }));

      if (error && error.message && typeof error.message === 'string' && error.message.includes('SUBSCRIPTION_INACTIVE_OR_DEVICE_UNREGISTERED')) {
        console.log('[AppGrid] Detected subscription/device registration error. Showing overlay.');
        showSubNoticeOverlay();
      } else {
        alert(`Download failed: ${error.message}`);
      }
    }
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
      {apps.map((app) => {
        // Calculate the progress prop for this specific app
        const progressProp = downloadProgress[app.id] ?? { status: 'idle', percentage: 0 };

        return (
          <AppCard
            key={app.id}
            app={app}
            onDownload={() => handleDownload(app.id)}
            progress={progressProp} // Pass the calculated prop
          />
        );
      })}
    </div>
  );
};
