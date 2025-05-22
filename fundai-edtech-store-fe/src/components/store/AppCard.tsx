import React, { useState, useEffect } from 'react';
import { App } from '../../types/app';

// Add this before AppCardProps
interface DownloadProgress {
  status: 'idle' | 'downloading' | 'complete' | 'error' | 'cancelled';  // strict union type of allowed states
  percentage: number;
  error?: string;
  path?: string;
}

interface AppCardProps {
  app: App;
  onDownload: (appId: string) => void;
  progress: DownloadProgress;
}

export const AppCard: React.FC<AppCardProps> = ({ app, onDownload, progress }) => {
  // Local state for isDownloading
  const [isDownloading, setIsDownloading] = useState(false);

  // Log the incoming progress prop
  console.log(`[AppCard ${app.id}] Received progress prop:`, JSON.stringify(progress));

  // Ensure we have a valid progress object with default values
  const currentProgress = {
    status: progress?.status || 'idle',
    percentage: progress?.percentage || 0,
    error: progress?.error,
    path: progress?.path
  };

  // Log the derived currentProgress object
  console.log(`[AppCard ${app.id}] Derived currentProgress:`, JSON.stringify(currentProgress));
  console.log(`[AppCard ${app.id}] Status for rendering: ${currentProgress.status}, Path for rendering: ${currentProgress.path}`);

  // Use useEffect to update isDownloading when status changes
  useEffect(() => {
    // Log status for isDownloading effect
    console.log(`[AppCard ${app.id}] useEffect for isDownloading - currentProgress.status:`, currentProgress.status);
    setIsDownloading(currentProgress.status === 'downloading');
  }, [currentProgress.status, app.id]);

  console.log(`[AppCard ${app.id}] Progress state:`, {
    progress,
    isDownloading,
    status: currentProgress.status
  });

  // Use useEffect to log when props change
  // React.useEffect(() => {
  //   console.log(`[AppCard] Progress prop changed for app ${app.id}:`, progress);
  // }, [progress, app.id]);

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
                  style={{ width: `${currentProgress.percentage}%` }}
                ></div>
              </div>
              <span className="text-sm text-muted-foreground">{currentProgress.percentage}%</span>
            </div>
          ) : currentProgress.status === 'complete' ? (
            <div className="text-center text-xs text-green-700 dark:text-green-400 py-2 px-1 break-all">
              {currentProgress.path ? (
                <>
                  Downloaded: <span className="font-medium">{currentProgress.path}</span>
                </>
              ) : (
                'Download Complete'
              )}
            </div>
          ) : currentProgress.status === 'error' ? (
             <div className="text-center text-red-500 text-sm">
               Error: {currentProgress.error?.substring(0, 50) || 'Download failed'}
             </div>
          ) : currentProgress.status === 'cancelled' ? (
            <div className="text-center text-yellow-500 text-sm">
              Download Cancelled
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
