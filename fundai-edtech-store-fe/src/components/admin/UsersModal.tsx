import React, { useState } from 'react';
import UsersTable from './UsersTable';
import RegisterDeviceForm from './RegisterDeviceForm';

// --- ADDED: Simple Success Overlay Component ---
const SuccessOverlay = () => (
  <div className="absolute inset-0 bg-green-500 bg-opacity-70 flex items-center justify-center z-10">
    <svg className="w-24 h-24 text-white animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  </div>
);
// --- END ADD ---

// --- ADDED: Simple Toast Notification Component ---
const Toast = ({ message, onClose }: { message: string; onClose: () => void }) => (
  <div className="fixed top-5 right-5 bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded shadow-lg z-[100] flex items-center justify-between">
    <span>{message}</span>
    <button onClick={onClose} className="ml-4 text-yellow-900 font-bold">&times;</button>
  </div>
);
// --- END ADD ---

interface UsersModalProps {
  onClose: () => void;
}

const UsersModal: React.FC<UsersModalProps> = ({ onClose }) => {
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
  // --- ADDED: State for success overlay, toast, and table refresh key ---
  const [showSuccessOverlay, setShowSuccessOverlay] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [userTableKey, setUserTableKey] = useState(0); // Key to force UsersTable refresh
  // --- END ADD ---

  const handleRegistrationResult = (result: { success: boolean; message: string }) => {
    // Clear previous messages
    setFeedbackMessage(null);
    setToastMessage(null);

    if (result.success) {
      // --- MODIFIED: Show success overlay, increment key ---
      setFeedbackMessage({ type: 'success', text: result.message }); // Keep simple feedback too
      setShowSuccessOverlay(true);
      setUserTableKey(prevKey => prevKey + 1); // Increment key to refresh table
      // Hide overlay after a short delay
      setTimeout(() => setShowSuccessOverlay(false), 1500); // 1.5 seconds
      // Clear success feedback message after longer delay
      setTimeout(() => setFeedbackMessage(null), 6000);
      // --- END MODIFY ---
    } else {
      // --- MODIFIED: Check for specific conflict errors ---
      const message = result.message;
      if (message.includes('Conflict: This Hardware ID already registered') ||
          message.includes('Conflict: This User already has an active device'))
      {
        setToastMessage(message); // Show toast for specific conflicts
        // Auto-hide toast after a delay
        setTimeout(() => setToastMessage(null), 6000);
      } else {
        // Show generic error feedback for other failures
        setFeedbackMessage({ type: 'error', text: message });
        setTimeout(() => setFeedbackMessage(null), 6000); // Auto-hide generic error too
      }
      // --- END MODIFY ---
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      {/* --- ADDED: Toast rendering --- */}
      {toastMessage && <Toast message={toastMessage} onClose={() => setToastMessage(null)} />}
      {/* --- END ADD --- */}

      {/* --- MODIFIED: Added position:relative for overlay --- */}
      <div
        className="bg-white dark:bg-[#363B54] rounded-lg shadow-xl w-[90%] max-w-6xl max-h-[90vh] flex flex-col overflow-hidden relative" // <-- Added relative positioning
        onClick={e => e.stopPropagation()}
      >
        {/* --- ADDED: Success Overlay rendering --- */}
        {showSuccessOverlay && <SuccessOverlay />}
        {/* --- END ADD --- */}

        <div className="p-4 flex justify-between items-center border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            User Management
          </h2>
          <button 
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 
              dark:hover:text-gray-200 transition-colors p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
            aria-label="Close modal"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-grow overflow-y-auto p-6 space-y-6">
          <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg shadow-sm border dark:border-gray-700">
            <h3 className="text-lg font-medium mb-3 text-gray-800 dark:text-gray-200">Register New Device</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Enter the user's email and the unique hardware ID provided by the user. If the email doesn't exist, provide the full details to create a new user account linked to this device.
            </p>
            <RegisterDeviceForm onResult={handleRegistrationResult} />
            {feedbackMessage && (
              <div
                className={`mt-3 px-4 py-2 rounded text-sm ${feedbackMessage.type === 'success'
                    ? 'bg-green-100 text-green-800 border border-green-300 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700'
                    : 'bg-red-100 text-red-800 border border-red-300 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700'
                  }`}
                role="alert"
              >
                {feedbackMessage.text}
              </div>
            )}
          </div>

          <div>
            <h3 className="text-lg font-medium mb-3 text-gray-800 dark:text-gray-200">Existing Users</h3>
            <div className="overflow-x-auto rounded-lg border dark:border-gray-700">
              <UsersTable key={userTableKey} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UsersModal;
