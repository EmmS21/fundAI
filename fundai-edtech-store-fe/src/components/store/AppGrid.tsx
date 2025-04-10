import React, { useEffect } from 'react';
import { App } from '../../types/app';
import { AppCard } from './AppCard';
import { useAppStore } from '../../stores/appStore';
import { useUIStore } from '../../stores/uiStore';

interface AppGridProps {
  apps: App[];
  onAppClick?: (app: App) => void;
}

export const AppGrid: React.FC<AppGridProps> = ({ apps, onAppClick }) => {
  const { loadApps, syncApps, isOffline } = useAppStore();
  const { showSubNoticeOverlay } = useUIStore();

  useEffect(() => {
    loadApps();
    const syncInterval = setInterval(() => {
        if (!isOffline) {
            syncApps();
        }
    }, 15 * 60 * 1000);
    return () => clearInterval(syncInterval);
  }, [loadApps, syncApps, isOffline]);

  const handleDownload = async (appId: string) => {
    if (isOffline) {
        console.log('[AppGrid] Download attempt while offline.');
        alert("Cannot start download while offline.");
        return;
    }

    console.log(`[AppGrid] Attempting download for appId: ${appId}`);
    try {
      await window.electronAPI.downloadApp(appId);
      console.log(`[AppGrid] downloadApp IPC call seems succeeded for ${appId}`);
    } catch (error: any) {
      console.error(`[AppGrid] Error invoking downloadApp for ${appId}:`, error);
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
      {apps.map((app) => (
        <AppCard
          key={app.id}
          app={app}
          onDownload={handleDownload}
        />
      ))}
    </div>
  );
};
