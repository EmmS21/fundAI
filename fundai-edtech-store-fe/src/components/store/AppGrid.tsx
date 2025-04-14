import React, { useState, useEffect, useCallback } from 'react';
import { App } from '../../types/app';
import { AppCard } from './AppCard';
import { useAppStore } from '../../stores/appStore';
import { useUIStore } from '../../stores/uiStore';

// Type definitions for API and Events (consider moving to a d.ts file)
// Ensure this matches what's exposed in preload.js under 'electronAPI'
interface ElectronAPI {
    getApps: () => Promise<App[]>;
    downloadApp: (args: { appId: string; filename: string }) => Promise<any>;
    onDownloadProgress: (callback: (data: DownloadProgressData) => void) => void;
    onDownloadComplete: (callback: (data: DownloadCompleteData) => void) => void;
    onDownloadError: (callback: (data: DownloadErrorData) => void) => void;
    onDownloadCancelled: (callback: (data: DownloadCancelledData) => void) => void;
    removeListener: (channel: string, callback: (...args: any[]) => void) => void;
    // Add ALL other methods exposed under electronAPI in preload.js
    syncApps: () => Promise<any>;
    getAppDetails: (appId: string) => Promise<any>;
    adminLogin: (credentials: any) => Promise<any>;
    checkAdmin: () => Promise<boolean>;
    clearAuth: () => Promise<boolean>;
    adminRegisterDevice: (deviceData: any) => Promise<any>;
    getUsers: () => Promise<any[]>;
    updateUserStatus: (userId: string, status: string) => Promise<any>;
    deleteUser: (userId: string) => Promise<any>;
    updateUserSubscription: (userId: string, payload: any) => Promise<any>;
    deleteUserSubscription: (userId: string) => Promise<any>;
    subscribeUser: (userId: string) => Promise<any>;
    getBooks: () => Promise<any[]>; // Assuming Book[] type exists
    onUpdateAvailable: (callback: (info: any) => void) => void;
    onUpdateProgress: (callback: (progress: any) => void) => void;
    onUpdateDownloaded: (callback: (info: any) => void) => void;
    onUpdateError: (callback: (errorMessage: string) => void) => void;
    restartApp: () => void;
    removeAllUpdateListeners: () => void;
    getAppVersion: () => Promise<string>;
}

declare global {
    interface Window {
        electronAPI: ElectronAPI;
        // Keep the other bridge if needed
         electron: {
            onDownloadDuplicateFound: (callback: (data: any) => void) => void;
            sendDownloadDuplicateResponse: (response: any) => void;
            removeDuplicateListener: (callback: (...args: any[]) => void) => void;
            openFile: (filePath: string) => void;
            showItemInFolder: (filePath: string) => void;
         }
    }
}

// Interfaces for Download Events Data (match data sent from main.js)
interface DownloadProgressData {
  appId?: string; // Make appId optional if sometimes only filename is sent
  filename: string;
  percentage: number;
  path: string;
  transferred: number;
  total: number;
}
interface DownloadCompleteData {
  appId?: string;
  filename: string;
  path: string;
}
interface DownloadErrorData {
  appId?: string;
  filename: string;
  error: string;
}
// --- Interface for Cancelled Data ---
interface DownloadCancelledData {
    filename: string;
    appId?: string; // Include appId if main.js sends it
}

// Define the structure for progress state
interface DownloadProgress {
  status: 'idle' | 'downloading' | 'complete' | 'error'; // Use strict types
  percentage: number;
  error?: string;
}
type AppDownloadProgressMap = { [appId: string]: DownloadProgress; };
interface AppGridProps { apps: App[]; onAppClick?: (app: App) => void; }

export const AppGrid: React.FC<AppGridProps> = ({ apps, onAppClick }) => {
  const { loadApps, syncApps, isOffline } = useAppStore();
  const { showSubNoticeOverlay } = useUIStore();
  const [downloadProgress, setDownloadProgress] = useState<AppDownloadProgressMap>({});

  // Add an effect to log state changes
  React.useEffect(() => {
    console.log('[AppGrid] Download progress state changed:', downloadProgress);
  }, [downloadProgress]);

  // Helper to find appId consistently
  const findAppId = useCallback((filename: string): string | undefined => {
      // Find app where app.name matches the filename received from the event
      const foundApp = apps.find(app => app.name === filename);
      return foundApp?.id;
  }, [apps]); // Dependency on 'apps' state is crucial

  useEffect(() => {
    loadApps();
    const syncInterval = setInterval(() => {
      if (!isOffline) { syncApps(); }
    }, 15 * 60 * 1000);

    // --- Listener Handlers ---
    const handleProgress = (data: DownloadProgressData) => {
      // Try finding appId using the helper, prioritize data.appId if present
      const appId = data.appId || findAppId(data.filename);
      if (!appId) return;
      setDownloadProgress(prev => ({ ...prev, [appId]: { ...prev[appId], status: 'downloading', percentage: data.percentage } }));
    };

    const handleComplete = (data: DownloadCompleteData) => {
      const appId = data.appId || findAppId(data.filename);
      if (!appId) return;
      console.log(`[AppGrid] Complete ${appId}`);
      setDownloadProgress(prev => ({ ...prev, [appId]: { status: 'complete', percentage: 100, error: undefined } }));
    };

    const handleError = (data: DownloadErrorData) => {
      const appId = data.appId || findAppId(data.filename);
      if (!appId) return;
      console.error(`[AppGrid] Error ${appId}: ${data.error}`);
      setDownloadProgress(prev => ({ ...prev, [appId]: { ...prev[appId], status: 'error', error: data.error } }));
    };

    const handleCancelled = (data: DownloadCancelledData) => {
        console.log(`[AppGrid handleCancelled] START - Received event:`, data);
        const appId = data.appId;
        if (!appId) {
            console.warn('[AppGrid handleCancelled] No appId in cancellation event:', data);
            return;
        }

        console.log(`[AppGrid handleCancelled] Setting progress for ${appId} to cancelled`);
        setDownloadProgress(prev => {
            console.log(`[AppGrid handleCancelled] Previous state:`, prev);
            const newState = {
                ...prev,
                [appId]: { status: 'cancelled', percentage: 0 }
            };
            console.log(`[AppGrid handleCancelled] New state:`, newState);
            return newState;
        });
    };

    // Add logging for event registration
    console.log('[AppGrid] Setting up download-cancelled event listener');
    window.electronAPI.onDownloadCancelled(handleCancelled);

    // Register listeners using window.electronAPI
    const api = window.electronAPI;
    if (api) {
        // Add direct registration for each event
        api.onDownloadProgress(handleProgress);
        api.onDownloadComplete(handleComplete);
        api.onDownloadError(handleError);
        api.onDownloadCancelled(handleCancelled); // This is the critical one

        // Keep track for cleanup
        const listeners = [
            { channel: 'download-progress', handler: handleProgress },
            { channel: 'download-complete', handler: handleComplete },
            { channel: 'download-error', handler: handleError },
            { channel: 'download-cancelled', handler: handleCancelled }
        ];

        // Cleanup function
        return () => {
            console.log("[AppGrid] Cleanup initiated.");
            clearInterval(syncInterval);
            
            if (api.removeListener) {
                listeners.forEach(({ channel, handler }) => {
                    api.removeListener(channel, handler);
                });
            }
            console.log('[AppGrid] Cleaning up download-cancelled event listener');
        };
    }

  }, [apps, findAppId, isOffline, loadApps, syncApps]);


  const handleDownload = async (appId: string, filename: string) => {
    console.log(`[AppGrid handleDownload] Starting download for ${appId}`);
    
    setDownloadProgress(prev => ({
      ...prev,
      [appId]: { status: 'downloading', percentage: 0, error: undefined }
    }));

    try {
      const result = await window.electronAPI.downloadApp({ appId, filename });
      console.log(`[AppGrid handleDownload] Download result:`, result);
    } catch (error) {
      console.error(`[AppGrid handleDownload] Error:`, error);
      setDownloadProgress(prev => ({
        ...prev,
        [appId]: { status: 'error', percentage: 0, error: error.message }
      }));
    }
  };


  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
      {apps.map((app) => {
        const progressProp = downloadProgress[app.id] ?? { status: 'idle', percentage: 0 };
        // --- Use app.name as filename ---
        const filenameToUse = app.name || `${app.id}-download`; // Fallback if name is missing

        // --- TEMPORARY LOG ---
        // console.log(`[AppGrid Rendering] App: ${app.id}, Progress being passed to AppCard:`, progressProp);
        // --------------------

        return (
          <AppCard
            key={app.id}
            app={app}
            onDownload={() => handleDownload(app.id, filenameToUse)}
            progress={progressProp}
          />
        );
      })}
    </div>
  );
};
