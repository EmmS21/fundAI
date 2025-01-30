import React from 'react';
import UsersTable from './UsersTable';
import { useAuth } from '../../hooks/useAuth';

interface UsersModalProps {
  onClose: () => void;
}

const UsersModal: React.FC<UsersModalProps> = ({ onClose }) => {
  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center">
      <div 
        className="bg-white dark:bg-[#363B54] rounded-lg shadow-xl w-[90%] max-w-6xl max-h-[90vh] overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="p-6 flex justify-between items-center border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            User Management
          </h2>
          <button 
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 
              dark:hover:text-gray-200 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6">
          <UsersTable />
        </div>
      </div>
    </div>
  );
};

export default UsersModal;
