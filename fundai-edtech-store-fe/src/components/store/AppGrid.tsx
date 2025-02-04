import React, { useEffect } from 'react';
import { App } from '../../types/app';
import { AppCard } from './AppCard';
import { useAppStore } from '../../stores/appStore';

interface AppGridProps {
  apps: App[];
  onAppClick: (app: App) => void;
}

export const AppGrid: React.FC<AppGridProps> = ({ apps, onAppClick }) => {
  const { loadApps, syncApps, isOffline } = useAppStore();

  useEffect(() => {
    loadApps();
    
    const syncInterval = setInterval(syncApps, 15 * 60 * 1000);
    return () => clearInterval(syncInterval);
  }, []);

  const handleDownload = (appId: string) => {
    window.electronAPI.downloadApp(appId);
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
      {apps.map((app) => (
        <AppCard
          key={app.id}
          app={app}
          onClick={() => onAppClick(app)}
          onDownload={handleDownload}
        />
      ))}
    </div>
  );
};
