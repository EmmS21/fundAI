import React, { useEffect, useState } from 'react';
import { AppGrid } from '../components/store/AppGrid';
import { SearchBar } from '../components/store/SearchBar';
import { CategoryFilter } from '../components/store/CategoryFilter';
import { UploadModal } from '../components/admin/UploadModal';
import { App } from '../types/app';

export default function Store() {
  const [apps, setApps] = useState<App[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);

  useEffect(() => {
    loadApps();
  }, []);

  const loadApps = async () => {
    setLoading(true);
    setError(null);
    try {
      const fetchedApps = await window.electronAPI.getApps();
      console.log('[Store.tsx] Apps received from electronAPI.getApps:', fetchedApps);
      setApps(fetchedApps);
    } catch (err) {
      console.error('[Store.tsx] Error loading apps:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        {loading ? (
          <div className="text-gray-600 dark:text-gray-300">Loading...</div>
        ) : error ? (
          <div className="text-red-500 dark:text-red-400">Error: {error}</div>
        ) : (
          <AppGrid apps={apps} />
        )}

        {showUploadModal && (
          <UploadModal 
            onClose={() => setShowUploadModal(false)}
            onUpload={async (formData) => {
              console.log('[Store.tsx] Upload initiated with:', formData);
              setShowUploadModal(false);
              loadApps();
            }}
          />
        )}
      </div>
    </div>
  );
}
