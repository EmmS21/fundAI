import React from 'react';
import { App } from '../../types/app';

interface AppCardProps {
  app: App;
  onDownload: (appId: string) => void;
}

export const AppCard: React.FC<AppCardProps> = ({ app, onDownload }) => {
  return (
    <div className="border rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
      <h3 className="text-lg font-semibold">{app.name}</h3>
      <p className="text-gray-600 text-sm mt-2">{app.description}</p>
      <div className="mt-4 flex justify-between items-center">
        <span className="text-sm text-gray-500">v{app.version}</span>
        <button 
          onClick={() => onDownload(app.id)}
          className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
        >
          Download
        </button>
      </div>
    </div>
  );
};
