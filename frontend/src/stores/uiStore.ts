import { create } from 'zustand';

interface UIState {
  fontSize: number;
  setFontSize: (size: number) => void;
}

export const useUIStore = create<UIState>((set) => ({
  fontSize: Number(localStorage.getItem('pct_fontSize')) || 14,
  setFontSize: (size) => {
    localStorage.setItem('pct_fontSize', String(size));
    set({ fontSize: size });
  },
}));
