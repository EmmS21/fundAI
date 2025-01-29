import React, { useEffect, useState } from 'react';

interface CategoryFilterProps {
  onCategoryChange?: (category: string) => void;
  onUploadClick: () => void;
}

export const CategoryFilter: React.FC<CategoryFilterProps> = ({ onCategoryChange, onUploadClick }) => {
  const [isAdminState, setIsAdminState] = useState(false);

  useEffect(() => {
    const checkAdmin = async () => {
      const adminStatus = await window.electronAPI.checkAdmin();
      console.log('CategoryFilter - Admin status:', adminStatus);
      setIsAdminState(adminStatus);
    };
    checkAdmin();
  }, []);

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
          onClick={() => {
            console.log('1. Upload button clicked in CategoryFilter');
            onUploadClick();
          }}
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
