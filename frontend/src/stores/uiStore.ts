/** UI store — sidebar, theme, panel state. */

import { create } from 'zustand';

interface UIState {
  sidebarOpen: boolean;
  taskPanelOpen: boolean;
  taskPanelWidth: number;
  theme: 'light' | 'dark';
  toggleSidebar: () => void;
  setTaskPanelOpen: (open: boolean) => void;
  setTaskPanelWidth: (width: number) => void;
  setTheme: (theme: 'light' | 'dark') => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  taskPanelOpen: false,
  taskPanelWidth: 520,
  theme: 'light',
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setTaskPanelOpen: (open) => set({ taskPanelOpen: open }),
  setTaskPanelWidth: (width) => set({ taskPanelWidth: Math.min(900, Math.max(500, width)) }),
  setTheme: (theme) => set({ theme }),
}));
