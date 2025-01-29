import React, { useState } from 'react';
import Store from './pages/Store';
import Library from './pages/Library';
import { Header } from './components/layout/Header';
import { ThemeProvider } from './context/ThemeContext';
import LoginModal from './components/auth/LoginModal';

export default function App() {
  const [activeTab, setActiveTab] = useState<'apps' | 'library'>('apps');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);

  const handleLoginClick = () => {
    setShowLoginModal(true);
  };

  const handleLoginSuccess = () => {
    setIsLoggedIn(true);
    setShowLoginModal(false);
  };

  const handleCloseModal = () => {
    setShowLoginModal(false);
  };

  return (
    <ThemeProvider>
      <div className="min-h-screen bg-white dark:bg-gray-900 transition-colors">
        {!isLoggedIn && (
          <button
            onClick={handleLoginClick}
            className="fixed top-4 left-4 z-50 px-4 py-2 bg-blue-500 text-white rounded-full 
              hover:bg-blue-600 transition-colors text-sm font-medium"
          >
            Login
          </button>
        )}
        
        <Header activeTab={activeTab} onTabChange={setActiveTab} />
        
        {showLoginModal && (
          <div 
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 
              flex items-center justify-center"
            onClick={handleCloseModal}
          >
            <div onClick={e => e.stopPropagation()}>
              <LoginModal 
                onLoginSuccess={handleLoginSuccess} 
                onClose={handleCloseModal}
              />
            </div>
          </div>
        )}
        
        <main>
          {activeTab === 'apps' ? <Store /> : <Library />}
        </main>
      </div>
    </ThemeProvider>
  );
}
