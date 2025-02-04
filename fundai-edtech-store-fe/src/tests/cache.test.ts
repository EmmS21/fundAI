import { useAppStore } from '@/stores/appStore';

describe('App Store Cache', () => {
  beforeEach(() => {
    // Reset store state
    const store = useAppStore.getState();
    store.apps = [];
    store.isOffline = false;
    store.lastSync = null;
  });

  it('should load apps from cache when online', async () => {
    const mockApps = [{ id: '1', name: 'Test App' }];
    
    // Mock window.electronAPI
    window.electronAPI.getApps = jest.fn().mockResolvedValueOnce(mockApps);
    
    await useAppStore.getState().loadApps();
    
    expect(useAppStore.getState().apps).toEqual(mockApps);
    expect(useAppStore.getState().isOffline).toBe(false);
  });

  it('should handle offline state when loading fails', async () => {
    // Mock failed API call
    window.electronAPI.getApps = jest.fn().mockRejectedValueOnce(new Error('Network error'));
    
    await useAppStore.getState().loadApps();
    
    expect(useAppStore.getState().isOffline).toBe(true);
    expect(useAppStore.getState().apps).toEqual([]);
  });

  it('should sync apps and update cache', async () => {
    const mockResult = { updated: true, count: 1 };
    window.electronAPI.syncApps = jest.fn().mockResolvedValueOnce(mockResult);
    window.electronAPI.getApps = jest.fn().mockResolvedValueOnce([{ id: '1', name: 'Updated App' }]);
    
    await useAppStore.getState().syncApps();
    
    expect(useAppStore.getState().isOffline).toBe(false);
    expect(useAppStore.getState().lastSync).toBeDefined();
  });
}); 