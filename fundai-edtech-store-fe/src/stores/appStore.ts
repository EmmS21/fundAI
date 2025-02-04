import { create } from 'zustand';

interface AppState {
  apps: any[];
  isLoading: boolean;
  isOffline: boolean;
  lastSync: Date | null;
  loadApps: () => Promise<void>;
  syncApps: () => Promise<void>;
}

export const useAppStore = create<AppState>()((set, get) => ({
  apps: [],
  isLoading: false,
  isOffline: false,
  lastSync: null,

  loadApps: async () => {
    set({ isLoading: true });
    try {
      const apps = await window.electronAPI.getApps();
      set({ apps, isLoading: false });
    } catch (error) {
      set({ isLoading: false, isOffline: true });
      console.error('Failed to load apps:', error);
    }
  },

  syncApps: async () => {
    try {
      const result = await window.electronAPI.syncApps();
      if (result.updated) {
        await get().loadApps();
      }
      set({ lastSync: new Date(), isOffline: false });
    } catch (error) {
      set({ isOffline: true });
      console.error('Sync failed:', error);
    }
  }
}));
