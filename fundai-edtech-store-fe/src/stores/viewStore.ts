import { create } from 'zustand';

interface ViewState {
  isLibraryView: boolean;
  setIsLibraryView: (isLibrary: boolean) => void;
}

export const useViewStore = create<ViewState>((set: (arg0: { isLibraryView: any; }) => any) => ({
  isLibraryView: false,
  setIsLibraryView: (isLibrary: any) => set({ isLibraryView: isLibrary }),
}));
