import React, { useState, useEffect } from 'react';
import Store from './pages/Store';
import Library from './pages/Library';
import { Header } from './components/layout/Header';
import { ThemeProvider } from './context/ThemeContext';
import LoginModal from './components/auth/LoginModal';
import { useAuth } from './hooks/useAuth';

export default function App() {
  const [activeTab, setActiveTab] = useState<'apps' | 'library'>('apps');
  const [showLoginModal, setShowLoginModal] = useState(false);
  const { isAdmin, clearAuth } = useAuth();

  useEffect(() => {
    const checkAdminStatus = async () => {
      const adminStatus = await window.electronAPI.checkAdmin();
      useAuth.getState().setAuth(null, adminStatus);
    };
    checkAdminStatus();
  }, []);

  const handleLoginClick = () => {
    setShowLoginModal(true);
  };

  const handleLoginSuccess = () => {
    setShowLoginModal(false);
  };

  const handleSignOut = async () => {
    console.log('triggered');
    try {
      await window.electronAPI.clearAuth();
      clearAuth(); // This clears Zustand store
      
      // Add this: Re-check admin status
      const adminStatus = await window.electronAPI.checkAdmin();
      console.log('New admin status after signout:', adminStatus);
      
    } catch (error) {
      console.error('Error in handleSignOut:', error);
    }
  };

  return (
    <ThemeProvider>
      <div className="min-h-screen bg-white dark:bg-gray-900 transition-colors">
        {!isAdmin ? (
          <button
            onClick={handleLoginClick}
            className="fixed top-4 left-4 z-50 px-4 py-2 bg-blue-500 text-white rounded-full 
              hover:bg-blue-600 transition-colors text-sm font-medium"
          >
            Login
          </button>
        ) : (
          <button
            onClick={handleSignOut}
            className="fixed top-4 left-4 z-50 px-4 py-2 bg-red-500 text-white rounded-full 
              hover:bg-red-600 transition-colors text-sm font-medium"
          >
            Sign Out
          </button>
        )}
        
        <Header activeTab={activeTab} onTabChange={setActiveTab} />
        
        {showLoginModal && (
          <div 
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 
              flex items-center justify-center"
            onClick={() => setShowLoginModal(false)}
          >
            <div onClick={e => e.stopPropagation()}>
              <LoginModal 
                onLoginSuccess={handleLoginSuccess} 
                onClose={() => setShowLoginModal(false)}
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
