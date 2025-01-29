import React, { useEffect, useState } from 'react';
import { SearchBar } from '../store/SearchBar';
import { CategoryFilter } from '../store/CategoryFilter';
import logoImage from '../../assets/logo.png'; 
import { ThemeToggle } from '../common/ThemeToggle';
import { useViewStore } from '../../stores/viewStore';

interface HeaderProps {
  activeTab: 'apps' | 'library';
  onTabChange: (tab: 'apps' | 'library') => void;
}

export const Header: React.FC<HeaderProps> = ({ activeTab, onTabChange }) => {
  const { setIsLibraryView } = useViewStore();
  const [isShrunk, setShrunk] = useState(false);

  useEffect(() => {
    const handler = () => {
      setShrunk((isShrunk) => {
        if (
          !isShrunk &&
          (document.body.scrollTop > 20 ||
            document.documentElement.scrollTop > 20)
        ) {
          return true;
        }

        if (
          isShrunk &&
          document.body.scrollTop < 4 &&
          document.documentElement.scrollTop < 4
        ) {
          return false;
        }

        return isShrunk;
      });
    };

    window.addEventListener("scroll", handler);
    return () => window.removeEventListener("scroll", handler);
  }, []);

  const handleTabChange = (tab: 'apps' | 'library') => {
    setIsLibraryView(tab === 'library');
    onTabChange(tab);
  };

  return (
    <div className={`bg-white dark:bg-gray-800 transition-all duration-200 sticky top-0 z-40
      ${isShrunk ? 'bg-opacity-90 backdrop-blur-md' : ''}`}>
      {/* Logo and Title Section */}
      <div className={`border-b border-gray-200 dark:border-gray-700 relative transition-all duration-200
        ${isShrunk ? 'py-2' : 'py-4'}`}>
        <div className="container mx-auto px-6">
          <ThemeToggle />
          <div className="flex flex-col items-center space-y-4">
            <img 
              src={logoImage}
              alt="FundaAI"
              className={`transition-all duration-200 ${isShrunk ? 'h-36' : 'h-72'}`}
            />
            <p className={`text-sm text-gray-600 dark:text-gray-300 text-center max-w-2xl transition-all
              ${isShrunk ? 'hidden' : 'block'}`}>
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
        <SearchBar />
        {activeTab === 'apps' && <CategoryFilter />}
      </div>
    </div>
  );
};
