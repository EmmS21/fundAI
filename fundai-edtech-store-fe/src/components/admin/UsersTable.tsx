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
    // Store original values to detect changes
    const originalStatus = user.status || 'inactive';
    const originalSubscriptionStatus = user.subscription_status || 'inactive';

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
        // Update original values if user prop changes while editing (unlikely but safe)
        // Note: This might reset edits if parent re-renders user unnecessarily.
        // Consider if this behavior is desired.
        // originalStatus = user.status || 'inactive';
        // originalSubscriptionStatus = user.subscription_status || 'inactive';
    }, [isEditing, user]);

    const handleSaveClick = async () => {
        setIsSaving(true);
        const userId = user.id!; // Assume ID is always present for existing users

        // --- Determine what actually changed ---
        const statusChanged = editedStatus !== originalStatus;
        const subscriptionRequested = originalSubscriptionStatus === 'inactive' && editedSubscriptionStatus === 'active';
        // Note: We ignore changes from active -> inactive for subscription via this save button.
        // Deleting/managing existing subscriptions would need separate handlers/UI.

        // --- Validate Email (client-side basic check) ---
        if (!editedEmail.trim()) {
             alert("Email cannot be empty."); // Keep basic client-side validation
             setIsSaving(false);
             return;
        }
        // --- Warn about unsaved changes (Email/Name) ---
        const otherDetailsChanged = editedEmail.trim() !== (user.email || '') || editedFullName.trim() !== (user.full_name || '');
        if (otherDetailsChanged) {
            // Inform user these fields aren't saved via this action
            console.warn("Changes to Email or Full Name cannot be saved via this interface yet.");
             // Optionally show an alert:
             // alert("Note: Changes to Email or Full Name cannot be saved currently.");
        }


        let errors: string[] = [];
        let successes: string[] = [];

        try {
            // --- 1. Update Status if changed ---
            if (statusChanged) {
                console.log(`[UserRow Save] Status changed for ${userId}. Calling updateUserStatus with '${editedStatus}'.`);
                try {
                    const result = await window.electronAPI.updateUserStatus(userId, editedStatus);
                    if (result.success) {
                        successes.push(`User status updated to ${editedStatus}.`);
                        // Update original status state *after* successful API call
                        // This requires passing setters or fetching data again.
                        // For now, the parent component handles refresh/state update.
                    } else {
                        throw new Error(result.error || 'Failed to update status.');
                    }
                } catch (err: any) {
                     console.error(`[UserRow Save] Error updating status for ${userId}:`, err);
                     errors.push(`Failed to update status: ${err.message}`);
                }
            }

            // --- 2. Subscribe User if requested (inactive -> active) ---
             if (subscriptionRequested) {
                 console.log(`[UserRow Save] Subscription requested for ${userId}. Calling subscribeUser.`);
                 try {
                     const result = await window.electronAPI.subscribeUser(userId);
                     if (result.success) {
                         successes.push(`New 30-day subscription created for user.`);
                         // Update original subscription status state *after* successful API call
                         // Similar challenge as above regarding state update.
                     } else {
                         // Handle specific "already exists" error
                         if (result.error?.includes("already exists")) {
                             errors.push("Subscription failed: User already has a subscription record.");
                         } else {
                            throw new Error(result.error || 'Failed to create subscription.');
                         }
                     }
                 } catch (err: any) {
                      console.error(`[UserRow Save] Error subscribing user ${userId}:`, err);
                      errors.push(`Failed to create subscription: ${err.message}`);
                 }
             }

             // --- 3. Handle results ---
             if (errors.length > 0) {
                 alert(`Errors occurred:\n- ${errors.join('\n- ')}`);
             } else if (successes.length > 0) {
                 alert(`Success:\n- ${successes.join('\n- ')}`);
                  // Call parent's save handler ONLY if there were actual changes processed
                  // This signals the parent (UsersModal) to potentially refresh data / exit edit mode
                 if (statusChanged || subscriptionRequested) {
                     // Pass only the *intended* final state based on successful operations.
                     // Since we don't directly update the local 'user' prop here,
                     // the parent needs to refresh data to see the real state.
                     // We pass the locally edited values, but acknowledge the parent refresh is key.
                     const finalUpdates = {
                        email: editedEmail.trim(), // Pass current value, even if not saved
                        fullName: editedFullName.trim(), // Pass current value, even if not saved
                        status: editedStatus, // Pass edited value (assuming success if statusChanged)
                        subscriptionStatus: editedSubscriptionStatus // Pass edited value (assuming success if subscriptionRequested)
                     };
                     await onSaveUpdates(userId, finalUpdates); // Notify parent
                 } else if (!statusChanged && !subscriptionRequested && otherDetailsChanged) {
                     // If only email/name changed, still notify parent to exit edit mode,
                     // but maybe without triggering a refresh if no backend call was made.
                     // Or just exit edit mode locally. For now, call parent's save handler.
                     await onSaveUpdates(userId, { email: editedEmail.trim(), fullName: editedFullName.trim(), status: originalStatus, subscriptionStatus: originalSubscriptionStatus });
                 } else if (!statusChanged && !subscriptionRequested && !otherDetailsChanged) {
                      // No changes were made or attempted, just cancel edit mode locally
                      onCancel(); // Call parent's cancel handler
                 }

             } else if (!otherDetailsChanged) {
                 // No relevant changes were made, just cancel edit mode
                 console.log("[UserRow Save] No relevant changes detected.");
                 onCancel(); // Exit edit mode via parent's cancel handler
             }


        } finally {
            setIsSaving(false);
            // The parent component (UsersModal -> UsersTable) is responsible
            // for setting editingUserId to null upon successful save via onSaveUserUpdates.
            // And potentially triggering a data refresh.
        }
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
