import React from 'react';
import { App } from '../../types/app';
import { AppCard } from './AppCard';

interface AppGridProps {
  apps: App[];
}

export const AppGrid: React.FC<AppGridProps> = ({ apps }) => {
  const handleDownload = (appId: string) => {
    window.electronAPI.downloadApp(appId);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {apps.map(app => (
        <AppCard 
          key={app.id} 
          app={app} 
          onDownload={handleDownload}
        />
      ))}
    </div>
  );
};
