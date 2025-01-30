import React, { useState } from 'react';
import { User } from '../../types/user';
import { useUsers } from '../../hooks/useUsers';

interface UserRowProps {
  user: User;
}

export const UserRow: React.FC<UserRowProps> = ({ user }) => {
  const [isDeleting, setIsDeleting] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const { updateUserStatus, deleteUser } = useUsers();

  const handleStatusToggle = async () => {
    setIsUpdating(true);
    try {
      const newStatus = user.status === 'active' ? 'inactive' : 'active';
      const success = await updateUserStatus(user.id, newStatus);
      if (!success) {
        throw new Error('Failed to update status');
      }
    } catch (error) {
      console.error('Failed to update user status:', error);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this user?')) return;
    
    setIsDeleting(true);
    try {
      const success = await deleteUser(user.id);
      if (!success) {
        throw new Error('Failed to delete user');
      }
    } catch (error) {
      console.error('Failed to delete user:', error);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <tr className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
        {user.email}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm">
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
          ${user.status === 'active' 
            ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
            : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
          }`}>
          {user.status}
        </span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm">
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
          ${user.subscription_status === 'active' 
            ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' 
            : 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
          }`}>
          {user.subscription_status}
        </span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 space-x-3">
        <button
          onClick={handleStatusToggle}
          disabled={isUpdating}
          className="text-blue-600 hover:text-blue-900 dark:text-blue-400 
            dark:hover:text-blue-300 disabled:opacity-50"
        >
          {isUpdating ? 'Updating...' : user.status === 'active' ? 'Deactivate' : 'Activate'}
        </button>
        <button
          onClick={handleDelete}
          disabled={isDeleting}
          className="text-red-600 hover:text-red-900 dark:text-red-400 
            dark:hover:text-red-300 disabled:opacity-50"
        >
          {isDeleting ? 'Deleting...' : 'Delete'}
        </button>
      </td>
    </tr>
  );
};
