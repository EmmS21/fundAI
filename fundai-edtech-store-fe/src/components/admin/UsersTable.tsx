import React, { useState, useEffect } from 'react';
import { User } from '../../types/user';

// Props required from UsersModal for editing logic
interface UsersTableProps {
  editingUserId: number | null;
  setEditingUserId: (userId: number | null) => void;
  onCancelEdit: () => void;
  onSaveUserUpdates: (userId: number, updates: {
    email: string;
    fullName: string;
    status: 'active' | 'inactive';
    subscriptionStatus: 'active' | 'inactive';
  }) => Promise<void>;
  // Removed onActivateSub - now handled via Save
}

// Extracted UserRow component for managing inline edit state
const UserRow: React.FC<{
    user: User;
    isEditing: boolean;
    onSetEditing: (id: number) => void;
    onCancel: () => void;
    onSaveUpdates: (id: number, updates: {
        email: string;
        fullName: string;
        status: 'active' | 'inactive';
        subscriptionStatus: 'active' | 'inactive';
    }) => Promise<void>;
}> = ({ user, isEditing, onSetEditing, onCancel, onSaveUpdates }) => {

    // State for editable fields, initialized from user prop
    const [editedEmail, setEditedEmail] = useState(user.email || '');
    const [editedFullName, setEditedFullName] = useState(user.full_name || '');
    const [editedStatus, setEditedStatus] = useState<'active' | 'inactive'>(user.status || 'inactive');
    const [editedSubscriptionStatus, setEditedSubscriptionStatus] = useState<'active' | 'inactive'>(user.subscription_status || 'inactive');

    const [isSaving, setIsSaving] = useState(false);

    // Function to reset local state to original user data
    const resetLocalState = () => {
        setEditedEmail(user.email || '');
        setEditedFullName(user.full_name || '');
        setEditedStatus(user.status || 'inactive');
        setEditedSubscriptionStatus(user.subscription_status || 'inactive');
    };

    // Reset local state if editing is cancelled externally or user data changes
    useEffect(() => {
        if (!isEditing) {
            resetLocalState();
        }
    }, [isEditing, user]);

    const handleSaveClick = async () => {
        setIsSaving(true);
        const updates = {
            email: editedEmail.trim(),
            fullName: editedFullName.trim(),
            status: editedStatus,
            subscriptionStatus: editedSubscriptionStatus
        };
        if (!updates.email) {
             alert("Email cannot be empty.");
             setIsSaving(false);
             return;
        }
        await onSaveUpdates(user.id!, updates);
        setIsSaving(false);
        // Parent (UsersModal) handles setting editingUserId to null on success
    };

    const handleEditButtonClick = () => {
        resetLocalState();
        onSetEditing(user.id!);
    };

    const handleCancelClick = () => {
        resetLocalState();
        onCancel();
    }

    // --- Styles ---
    const actionButtonClasses = "px-3 py-1 text-xs font-medium rounded transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed";
    const editButtonClasses = `${actionButtonClasses} text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 focus:ring-blue-500`;
    const saveButtonClasses = `${actionButtonClasses} text-white bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600 focus:ring-green-500`;
    const cancelButtonClasses = `${actionButtonClasses} text-gray-700 bg-gray-200 hover:bg-gray-300 dark:text-gray-200 dark:bg-gray-600 dark:hover:bg-gray-500 focus:ring-gray-500 ml-2`;
    const editableInputClasses = "block w-full px-2 py-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm text-gray-900 dark:text-gray-100";
    const tdClasses = "px-6 py-4 whitespace-nowrap text-sm"; // Restored padding
    const tdTextClasses = `${tdClasses} text-gray-500 dark:text-gray-300`;
    const tdIdClasses = `${tdClasses} font-medium text-gray-900 dark:text-gray-100`;
    // --- End Styles ---

    return (
         <tr key={user.id} className={isEditing ? 'bg-yellow-50 dark:bg-yellow-900/20' : ''}>
            {/* --- RENDER ALL DATA COLUMNS --- */}
            <td className={tdIdClasses}>{user.id}</td>

            {/* Email */}
            <td className={tdTextClasses}>
                {isEditing ? <input type="email" value={editedEmail} onChange={(e) => setEditedEmail(e.target.value)} className={editableInputClasses} disabled={isSaving} required /> : user.email}
            </td>

            {/* Full Name */}
            <td className={tdTextClasses}>
                 {isEditing ? <input type="text" value={editedFullName} onChange={(e) => setEditedFullName(e.target.value)} className={editableInputClasses} disabled={isSaving} /> : (user.full_name || '-')}
            </td>

             {/* Address (Read-Only) - Restored */}
             <td className={tdTextClasses}>{user.address || '-'}</td>

             {/* City (Read-Only) - Restored */}
             <td className={tdTextClasses}>{user.city || '-'}</td>

             {/* Country (Read-Only) - Restored */}
             <td className={tdTextClasses}>{user.country || '-'}</td>

            {/* Created At (Read-Only) */}
            <td className={tdTextClasses}>
                {user.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}
            </td>

            {/* Status */}
            <td className={tdClasses}>
                {isEditing ? (
                    <select value={editedStatus} onChange={(e) => setEditedStatus(e.target.value as 'active' | 'inactive')} className={editableInputClasses} disabled={isSaving}>
                        <option value="active">Active</option>
                        <option value="inactive">Inactive</option>
                    </select>
                ) : (
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${ user.status === 'active' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300' }`}> {user.status || 'inactive'} </span>
                )}
            </td>

            {/* Subscription */}
            <td className={tdClasses}>
                 {isEditing ? (
                     <select value={editedSubscriptionStatus} onChange={(e) => setEditedSubscriptionStatus(e.target.value as 'active' | 'inactive')} className={editableInputClasses} disabled={isSaving}>
                         <option value="active">Active (1 Month)</option>
                         <option value="inactive">Inactive</option>
                     </select>
                 ) : (
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${ user.subscription_status === 'active' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300' }`}> {user.subscription_status || 'inactive'} </span>
                 )}
            </td>

            {/* Actions */}
            <td className={`${tdClasses} font-medium space-x-2`}>
                {isEditing ? (
                    <>
                        <button onClick={handleSaveClick} className={saveButtonClasses} disabled={isSaving}> {isSaving ? 'Saving...' : 'Save'} </button>
                        <button onClick={handleCancelClick} className={cancelButtonClasses} disabled={isSaving}> Cancel </button>
                    </>
                ) : (
                    <button onClick={handleEditButtonClick} className={editButtonClasses}> Edit </button>
                )}
            </td>
         </tr>
    );
};


// Main UsersTable component - RESTORED DATA FETCHING
const UsersTable: React.FC<UsersTableProps> = ({
    editingUserId,
    setEditingUserId,
    onCancelEdit,
    onSaveUserUpdates,
    // Removed users, loading, error from props
}) => {
  // --- State moved back here ---
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // --- End State ---

  // --- useEffect for fetching moved back here ---
  useEffect(() => {
    const fetchUsers = async () => {
      try {
        setLoading(true);
        setError(null); // Clear previous error
        console.log('[UsersTable] Calling window.electronAPI.getUsers()...');
        const response = await window.electronAPI.getUsers();
        console.log('[UsersTable] Received response from IPC:', response);

        if (!Array.isArray(response)) {
          console.error('[UsersTable] Invalid response format - not an array:', response);
          throw new Error('Invalid response format');
        }

        console.log(`[UsersTable] Response is valid array with ${response.length} users. Setting state.`);
        setUsers(response);
      } catch (err) {
        console.error('[UsersTable] Error fetching or processing users:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch users');
        setUsers([]);
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
    // NOTE: If you need the table to refresh after a save in UsersModal,
    // UsersModal might need to pass down a 'refreshKey' prop similar
    // to what we had before, and add that key to this dependency array.
    // For now, keeping it simple to fetch only on mount.
  }, []); // Fetch on component mount
  // --- End useEffect ---


    if (loading) { return <div className="text-center p-4 dark:text-gray-400">Loading users...</div>; }
    if (error) { return <div className="text-center p-4 text-red-600 dark:text-red-400">Error: {error}</div>; }
    if (!users || users.length === 0) { return <div className="text-center p-4 dark:text-gray-400">No users found</div>; }

  return (
    <div className="overflow-x-auto rounded-lg shadow"> {/* Added back shadow */}
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            {/* --- Restored Headers --- */}
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"> ID </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"> Email </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"> Full Name </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"> Address </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"> City </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"> Country </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"> Created At </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"> Status </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"> Subscription </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"> Actions </th>
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
          {/* Use UserRow component */}
          {users.map((user) => (
             <UserRow
                key={user.id} // Unique key for React list rendering
                user={user}
                isEditing={user.id === editingUserId} // Check if this row is the one being edited
                onSetEditing={setEditingUserId} // Pass function to enter edit mode
                onCancel={onCancelEdit} // Pass function to cancel editing
                onSaveUpdates={onSaveUserUpdates} // Pass function to save changes
             />
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default UsersTable;
