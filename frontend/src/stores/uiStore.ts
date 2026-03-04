/** UI store — sidebar, theme, panel state, font sizing. */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UIState {
  sidebarOpen: boolean;
  taskPanelOpen: boolean;
  taskPanelWidth: number;
  theme: 'light' | 'dark';
  fontSize: number;
  toggleSidebar: () => void;
  setTaskPanelOpen: (open: boolean) => void;
  setTaskPanelWidth: (width: number) => void;
  setTheme: (theme: 'light' | 'dark') => void;
  setFontSize: (size: number) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      taskPanelOpen: false,
      taskPanelWidth: 520,
      theme: 'light',
      fontSize: 14,
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      setTaskPanelOpen: (open) => set({ taskPanelOpen: open }),
      setTaskPanelWidth: (width) => set({ taskPanelWidth: Math.min(900, Math.max(500, width)) }),
      setTheme: (theme) => set({ theme }),
      setFontSize: (size) => set({ fontSize: size }),
    }),
    {
      name: 'pct-ui',
      partialize: (state) => ({ fontSize: state.fontSize, theme: state.theme }),
    },
  ),
);
