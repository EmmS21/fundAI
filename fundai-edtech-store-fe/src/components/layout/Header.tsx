import React, { useEffect, useState } from 'react';
import { SearchBar } from '../store/SearchBar';
import { CategoryFilter } from '../store/CategoryFilter';
import logoImage from '../../assets/logo.png'; 
import { ThemeToggle } from '../common/ThemeToggle';
import { useViewStore } from '../../stores/viewStore';

interface HeaderProps {
  activeTab: 'apps' | 'library';
  onTabChange: (tab: 'apps' | 'library') => void;
  onUploadClick: () => void;
  onUsersClick: () => void;
}

export const Header: React.FC<HeaderProps> = ({ activeTab, onTabChange, onUploadClick, onUsersClick }) => {
  const { setIsLibraryView } = useViewStore();
  const [isShrunk, setShrunk] = useState(false);

  console.log('2. Header rendering with onUploadClick:', !!onUploadClick);

  useEffect(() => {
    const handler = () => {
      const currentScroll = window.scrollY || document.documentElement.scrollTop;
      setShrunk(currentScroll > 20);
    };

    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  const handleTabChange = (tab: 'apps' | 'library') => {
    setIsLibraryView(tab === 'library');
    onTabChange(tab);
  };

  return (
    <div className={`bg-white dark:bg-gray-800 transition-all duration-300 ease-out
      ${isShrunk ? 'bg-opacity-95 shadow-md' : ''}`}>
      
      <div className={`border-b border-gray-200 dark:border-gray-700 transition-all duration-300
        ${isShrunk ? 'py-2' : 'py-4'}`}>
        <div className="container mx-auto px-6">
          <ThemeToggle />
          <div className="flex flex-col items-center space-y-2">
            <img 
              src={logoImage}
              alt="FundaAI"
              className={`transition-all duration-300 ease-out
                ${isShrunk ? 'h-16' : 'h-72'}`}
            />
            <p className={`text-gray-600 dark:text-gray-300 text-center max-w-2xl transition-all duration-300
              ${isShrunk ? 'text-sm' : 'text-base'}`}>
              A store of linux native edtech apps using local AI models to help you learn new skills
            </p>
          </div>
        </div>
      </div>

      {/* Full-width Tab Navigation */}
      <div className="bg-gray-100 dark:bg-gray-700 shadow-sm">
        <div className="container mx-auto">
          <div className="grid grid-cols-2 w-full">
            <button
              onClick={() => handleTabChange('apps')}
              className={`py-4 text-lg font-medium transition-colors ${
                activeTab === 'apps'
                  ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white border-b-2 border-blue-500'
                  : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-gray-600'
              }`}
            >
              App Store
            </button>
            <button
              onClick={() => handleTabChange('library')}
              className={`py-4 text-lg font-medium transition-colors ${
                activeTab === 'library'
                  ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white border-b-2 border-blue-500'
                  : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-gray-600'
              }`}
            >
              Library
            </button>
          </div>
        </div>
      </div>

      {/* Search and Categories */}
      <div className="container mx-auto px-6 py-4 space-y-4 bg-white dark:bg-gray-800">
        <SearchBar activeTab={activeTab} />
        {activeTab === 'apps' && <CategoryFilter onUploadClick={onUploadClick} onUsersClick={onUsersClick} />}
      </div>
    </div>
  );
};
