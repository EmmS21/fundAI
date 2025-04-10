import React, { useState, useEffect } from 'react';
import UsersTable from './UsersTable';
import RegisterDeviceForm from './RegisterDeviceForm';
import { User } from '../../types/user';
import { UserDetailsPayload, UpdatedUserResponse } from '../../types/electron';

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
  const [showSuccessOverlay, setShowSuccessOverlay] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [usersError, setUsersError] = useState<string | null>(null);
  const [userTableKey, setUserTableKey] = useState(0);
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [isSavingUser, setIsSavingUser] = useState(false);

  const fetchUsers = async () => {
    try {
      setLoadingUsers(true);
      setUsersError(null);
      console.log('[UsersModal] fetchUsers started...'); // <-- Log Start
      const response = await window.electronAPI.getUsers();
      console.log('[UsersModal] fetchUsers - Received response from IPC:', response); // <-- Log IPC Response

      if (!Array.isArray(response)) {
        console.error('[UsersModal] fetchUsers - Invalid response format:', response); // <-- Log Invalid Format
        throw new Error('Invalid response format');
      }
      console.log(`[UsersModal] fetchUsers - Setting users state with ${response.length} users.`); // <-- Log State Set
      setUsers(response);
    } catch (err) {
      console.error('[UsersModal] fetchUsers - Error:', err); // <-- Log Error
      setUsersError(err instanceof Error ? err.message : 'Failed to fetch users');
      setUsers([]);
    } finally {
      console.log('[UsersModal] fetchUsers finished. Setting loadingUsers to false.'); // <-- Log Finish
      setLoadingUsers(false);
    }
  };

  useEffect(() => {
    console.log(`[UsersModal] useEffect triggered with key: ${userTableKey}. Fetching users.`); // <-- Log useEffect Trigger
    fetchUsers();
  }, [userTableKey]);

  const handleRegistrationResult = (result: { success: boolean; message: string }) => {
    setFeedbackMessage(null);
    setToastMessage(null);

    if (result.success) {
      setFeedbackMessage({ type: 'success', text: result.message });
      setShowSuccessOverlay(true);
      setUserTableKey(prevKey => prevKey + 1); // Increment key to refresh table
      setTimeout(() => setShowSuccessOverlay(false), 1500);
      setTimeout(() => setFeedbackMessage(null), 6000);
    } else {
        const message = result.message;
      if (message.includes('Conflict: This Hardware ID already registered') ||
          message.includes('Conflict: This User already has an active device'))
      {
        setToastMessage(message);
        setTimeout(() => setToastMessage(null), 6000);
      } else {
        setFeedbackMessage({ type: 'error', text: message });
        setTimeout(() => setFeedbackMessage(null), 6000);
      }
    }
  };

  const handleCancelEdit = () => {
      console.log('[UsersModal] Cancelling edit.');
      setEditingUserId(null);
  };

  const handleSaveUserUpdates = async (userId: string, updates: { email: string; fullName: string; status: 'active' | 'inactive'; subscriptionStatus: 'active' | 'inactive'; }) => {
      console.log(`[UsersModal] Attempting to save updates for user ID ${userId}:`, updates);
      setToastMessage(null);
      setIsSavingUser(true);

      try {
          const userDetailsPayload: UserDetailsPayload = {};
          let detailsChanged = false;

          if (typeof updates.fullName !== 'undefined') {
             userDetailsPayload.name = updates.fullName;
             detailsChanged = true;
          }
          if (typeof updates.email !== 'undefined') {
             userDetailsPayload.email = updates.email;
             detailsChanged = true;
          }
          if (typeof updates.status !== 'undefined') {
             userDetailsPayload.is_active = updates.status === 'active';
             detailsChanged = true;
          }

          let userUpdateResult: UpdatedUserResponse | null = null;
          if (detailsChanged) {
              console.log(`[UsersModal] Calling updateUserDetails for ${userId} with payload:`, userDetailsPayload);
              userUpdateResult = await window.electronAPI.updateUserDetails(userId, userDetailsPayload);
              console.log(`[UsersModal] updateUserDetails result for ${userId}:`, userUpdateResult);
          } else {
              console.log(`[UsersModal] No user details or status changes detected for user ${userId}. Skipping updateUserDetails call.`);
          }

          if (typeof updates.subscriptionStatus !== 'undefined') {
             console.warn(`[UsersModal] Subscription status change requested to '${updates.subscriptionStatus}' for user ${userId}. This requires specific API calls (PUT/DELETE with plan_id) not fully supported by this function's current structure. Skipping subscription update.`);
          }

          setToastMessage(`User details saved successfully for user ${userId}.`);
          setEditingUserId(null);
          setUserTableKey(prev => prev + 1);

          setTimeout(() => setToastMessage(null), 4000);

      } catch (error: any) {
            console.error(`[UsersModal] Error saving updates for user ${userId}:`, error);
            const errorMessage = error?.message || 'An unknown error occurred while saving user details.';
            setToastMessage(`Error: ${errorMessage}`);
      } finally {
          setIsSavingUser(false);
      }
  };

  // --- Add Log Before Rendering UsersTable ---
  console.log('[UsersModal] Rendering UsersTable with props:', { users, loadingUsers, usersError });

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      {toastMessage && <Toast message={toastMessage} onClose={() => setToastMessage(null)} />}

      <div
        className="bg-white dark:bg-[#363B54] rounded-lg shadow-xl w-[90%] max-w-6xl max-h-[90vh] flex flex-col overflow-hidden relative"
        onClick={e => e.stopPropagation()}
      >
        {showSuccessOverlay && <SuccessOverlay />}
        {/* Modal Header */}
        <div className="p-4 flex justify-between items-center border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
           <h2 className="text-xl font-semibold text-gray-900 dark:text-white">User Management</h2>
           <button onClick={onClose} className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700" aria-label="Close modal">
             <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
           </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-grow overflow-y-auto p-6 space-y-6">
          {/* Registration Section */}
          <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg shadow-sm border dark:border-gray-700">
              <h3 className="text-lg font-medium mb-3 text-gray-800 dark:text-gray-200">Register New Device</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">Enter the user's email and the unique hardware ID provided by the user. If the email doesn't exist, provide the full details to create a new user account linked to this device.</p>
              <RegisterDeviceForm onResult={handleRegistrationResult} />
              {feedbackMessage && <div className={`mt-3 px-4 py-2 rounded text-sm ${feedbackMessage.type === 'success' ? 'bg-green-100 text-green-800 border border-green-300 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700' : 'bg-red-100 text-red-800 border border-red-300 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700'}`} role="alert">{feedbackMessage.text}</div>}
          </div>

          {/* Users Table Section */}
          <div>
             <h3 className="text-lg font-medium mb-3 text-gray-800 dark:text-gray-200">Existing Users</h3>
            <div className="overflow-x-auto rounded-lg border dark:border-gray-700">
              <UsersTable
                key={userTableKey}
                users={users}
                loading={loadingUsers}
                error={usersError}
                editingUserId={editingUserId}
                setEditingUserId={setEditingUserId}
                onCancelEdit={handleCancelEdit}
                onSaveUserUpdates={handleSaveUserUpdates}
                isSaving={isSavingUser}
              />
            </div>
          </div>
        </div> {/* End Scrollable Content */}
      </div> {/* End Modal Content */}
    </div> /* End Modal Backdrop */
  );
};

export default UsersModal;
