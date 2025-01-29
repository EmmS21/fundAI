import { create } from 'zustand';

interface AuthState {
  isAdmin: boolean;
  token: string | null;
  setAuth: (token: string | null, isAdmin: boolean) => void;
  clearAuth: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  isAdmin: false,
  token: null,
  setAuth: (token, isAdmin) => set({ token, isAdmin }),
  clearAuth: () => set({ token: null, isAdmin: false })
}));
