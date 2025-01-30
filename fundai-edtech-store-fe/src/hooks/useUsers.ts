import { useState, useEffect } from 'react';
import { User } from '../types/user';

export const useUsers = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Fetch users on mount and when refresh is triggered
  useEffect(() => {
    const fetchUsers = async () => {
      try {
        setLoading(true);
        const fetchedUsers = await window.electronAPI.getUsers();
        setUsers(fetchedUsers);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch users');
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
  }, [refreshTrigger]);

  // Function to manually refresh users list
  const refreshUsers = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  // Function to update user status
  const updateUserStatus = async (userId: string, newStatus: 'active' | 'inactive') => {
    try {
      const success = await window.electronAPI.updateUserStatus(userId, newStatus);
      if (success) {
        // Update local state to reflect the change
        setUsers(prevUsers => 
          prevUsers.map(user => 
            user.id === userId 
              ? { ...user, status: newStatus }
              : user
          )
        );
        return true;
      }
      return false;
    } catch (err) {
      console.error('Failed to update user status:', err);
      return false;
    }
  };

  // Function to delete user
  const deleteUser = async (userId: string) => {
    try {
      const success = await window.electronAPI.deleteUser(userId);
      if (success) {
        // Remove user from local state
        setUsers(prevUsers => prevUsers.filter(user => user.id !== userId));
        return true;
      }
      return false;
    } catch (err) {
      console.error('Failed to delete user:', err);
      return false;
    }
  };

  return {
    users,
    loading,
    error,
    refreshUsers,
    updateUserStatus,
    deleteUser
  };
};
