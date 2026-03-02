/** Board store — client-side board state. */

import { create } from 'zustand';
import type { Feature, WorkflowStage } from '../types/board';

interface BoardState {
  features: Feature[];
  workflowStages: WorkflowStage[];
  selectedFeatureId: string | null;
  selectedTaskId: string | null;
  setBoard: (features: Feature[], stages: WorkflowStage[]) => void;
  selectFeature: (id: string | null) => void;
  selectTask: (featureId: string | null, taskId: string | null) => void;
}

export const useBoardStore = create<BoardState>((set) => ({
  features: [],
  workflowStages: [],
  selectedFeatureId: null,
  selectedTaskId: null,
  setBoard: (features, stages) => set({ features, workflowStages: stages }),
  selectFeature: (id) => set({ selectedFeatureId: id }),
  selectTask: (featureId, taskId) => set({ selectedFeatureId: featureId, selectedTaskId: taskId }),
}));
