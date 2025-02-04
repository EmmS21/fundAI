import React from 'react';

interface SearchBarProps {
  activeTab: 'apps' | 'library';
}

export const SearchBar: React.FC<SearchBarProps> = ({ activeTab }) => {
  return (
    <div className="relative">
      <input
        type="text"
        placeholder={activeTab === 'apps' ? "Search apps..." : "Search books..."}
        className="w-full pl-10 pr-4 py-2 bg-gray-100 dark:bg-gray-700 border-0 rounded-lg 
        focus:ring-2 focus:ring-blue-500 focus:bg-white dark:focus:bg-gray-600 
        text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400
        transition-colors"
      />
      <svg 
        className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 dark:text-gray-500"
        width="20" 
        height="20" 
        fill="none" 
        stroke="currentColor"
      >
        <path 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          strokeWidth="2" 
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
        />
      </svg>
    </div>
  );
};
