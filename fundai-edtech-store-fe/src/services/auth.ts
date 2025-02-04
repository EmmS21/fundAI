import { useAuth } from '../hooks/useAuth';

export const adminLogin = async (email: string, password: string) => {
  const result = await window.electronAPI.adminLogin({ email, password });
  if (result.success) {
    // This is where we need to set the admin status
    useAuth.getState().setAuth(null, result.isAdmin || false);
  }
  return result;
};
