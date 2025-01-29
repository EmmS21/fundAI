import React, { useEffect, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';

interface CategoryFilterProps {
  onCategoryChange?: (category: string) => void;
}

export const CategoryFilter: React.FC<CategoryFilterProps> = ({ onCategoryChange }) => {
  const [isAdminState, setIsAdminState] = useState(false);
  const { isAdmin } = useAuth(); // Get admin status from Zustand store

  useEffect(() => {
    const checkAdmin = async () => {
      const adminStatus = await window.electronAPI.checkAdmin();
      console.log('CategoryFilter - Admin status:', adminStatus);
      setIsAdminState(adminStatus);
    };
    
    // Check when component mounts and when isAdmin changes
    checkAdmin();
  }, [isAdmin]); // Add isAdmin as dependency

  return (
    <div className="flex space-x-4 overflow-x-auto pb-2">
      <button className="px-4 py-2 text-sm font-medium text-gray-900 dark:text-white 
        bg-gray-100 dark:bg-gray-700 rounded-full 
        hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">
        All Categories
      </button>
      <button className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 
        bg-gray-100 dark:bg-gray-700 rounded-full 
        hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">
        Mathematics
      </button>
      <button className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 
        bg-gray-100 dark:bg-gray-700 rounded-full 
        hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">
        Science
      </button>
      <button className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 
        bg-gray-100 dark:bg-gray-700 rounded-full 
        hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors">
        Programming
      </button>
      
      {isAdminState && (
        <button
          onClick={() => console.log('Upload clicked')}
          className="px-4 py-2 text-sm font-medium text-white
            bg-blue-500 rounded-full hover:bg-blue-600 
            transition-colors flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Upload
        </button>
      )}
    </div>
  );
};
