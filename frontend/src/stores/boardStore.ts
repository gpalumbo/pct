import { create } from 'zustand';

export interface PendingMove {
  featureId: string;
  taskId: string;
  newStatus: string;
}

interface BoardState {
  // Filters
  filterFeatureIds: string[];
  filterAgentTypes: string[];
  filterStatuses: string[];
  showSuspended: boolean;
  showComplete: boolean;

  // UI
  collapsedSwimlanes: Set<string>;
  isDragging: boolean;

  // Stage skip confirmation
  pendingMove: PendingMove | null;

  // Actions
  setFilterFeatureIds: (ids: string[]) => void;
  setFilterAgentTypes: (types: string[]) => void;
  setFilterStatuses: (statuses: string[]) => void;
  setShowSuspended: (show: boolean) => void;
  setShowComplete: (show: boolean) => void;
  toggleSwimlane: (featureId: string) => void;
  setIsDragging: (dragging: boolean) => void;
  setPendingMove: (move: PendingMove | null) => void;
}

export const useBoardStore = create<BoardState>((set) => ({
  filterFeatureIds: [],
  filterAgentTypes: [],
  filterStatuses: [],
  showSuspended: false,
  showComplete: false,

  collapsedSwimlanes: new Set<string>(),
  isDragging: false,

  pendingMove: null,

  setFilterFeatureIds: (ids) => set({ filterFeatureIds: ids }),
  setFilterAgentTypes: (types) => set({ filterAgentTypes: types }),
  setFilterStatuses: (statuses) => set({ filterStatuses: statuses }),
  setShowSuspended: (show) => set({ showSuspended: show }),
  setShowComplete: (show) => set({ showComplete: show }),
  toggleSwimlane: (featureId) =>
    set((state) => {
      const next = new Set(state.collapsedSwimlanes);
      if (next.has(featureId)) {
        next.delete(featureId);
      } else {
        next.add(featureId);
      }
      return { collapsedSwimlanes: next };
    }),
  setIsDragging: (dragging) => set({ isDragging: dragging }),
  setPendingMove: (move) => set({ pendingMove: move }),
}));
