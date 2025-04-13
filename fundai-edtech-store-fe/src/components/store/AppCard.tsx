import React from 'react';
import { App } from '../../types/app';

interface AppCardProps {
  app: App;
  onDownload: (appId: string) => void;
  progress: DownloadProgress;
}

export const AppCard: React.FC<AppCardProps> = ({ app, onDownload, progress }) => {
  const isDownloading = progress.status === 'downloading';
  const isComplete = progress.status === 'complete';
  return (
    <div className="border rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
      <h3 className="text-lg font-semibold">{app.name}</h3>
      <p className="text-gray-600 text-sm mt-2">{app.description}</p>
      <div className="mt-4 flex justify-between items-center">
        <span className="text-sm text-gray-500">v{app.version}</span>
        <div className="mt-auto pt-4">
          {isDownloading ? (
            <div className="text-center">
              <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
                <div
                  className="bg-blue-600 h-2.5 rounded-full"
                  style={{ width: `${progress.percentage}%` }}
                ></div>
              </div>
              <span className="text-sm text-muted-foreground">{progress.percentage}%</span>
            </div>
          ) : isComplete ? (
            <button className="w-full bg-green-600 text-white py-2 px-4 rounded hover:bg-green-700">
               Installed / Open
            </button>
          ) : progress.status === 'error' ? (
             <div className="text-center text-red-500 text-sm">
               Error: {progress.error?.substring(0, 50) || 'Download failed'}
             </div>
          ) : (
            <button
              className="w-full bg-primary text-primary-foreground py-2 px-4 rounded hover:bg-primary/90"
              onClick={() => onDownload(app.id)}
            >
              Download
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
