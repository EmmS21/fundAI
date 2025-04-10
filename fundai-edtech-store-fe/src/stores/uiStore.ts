import { create } from 'zustand';

interface UIState {
  isSubNoticeOverlayVisible: boolean;
  showSubNoticeOverlay: () => void;
  hideSubNoticeOverlay: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  isSubNoticeOverlayVisible: false,
  showSubNoticeOverlay: () => set({ isSubNoticeOverlayVisible: true }),
  hideSubNoticeOverlay: () => set({ isSubNoticeOverlayVisible: false }),
}));
