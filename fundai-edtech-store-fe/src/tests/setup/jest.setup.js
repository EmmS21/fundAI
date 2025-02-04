beforeEach(() => {
  // Reset all mocks before each test
  window.electronAPI = {
    getApps: jest.fn(),
    syncApps: jest.fn(),
    adminLogin: jest.fn(),
    getAppDetails: jest.fn(),
    downloadApp: jest.fn(),
    login: jest.fn(),
    onDownloadProgress: jest.fn(),
    onDownloadComplete: jest.fn(),
    checkAdmin: jest.fn(),
    clearAuth: jest.fn(),
    updateUserStatus: jest.fn(),
    deleteUser: jest.fn(),
    getUsers: jest.fn()
  };
});
