import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as api from '../api/boardApi';
import type {
  CreateFeatureRequest,
  CreateTaskRequest,
  MoveTaskRequest,
  UpdateFeatureMetadataRequest,
  UpdateTaskRequest,
} from '../types/board';

const BOARD_KEY = ['board'] as const;

// ---------------------------------------------------------------------------
// Board (composite)
// ---------------------------------------------------------------------------

export function useBoard() {
  return useQuery({
    queryKey: BOARD_KEY,
    queryFn: api.fetchBoard,
    refetchInterval: 10_000,
  });
}

// ---------------------------------------------------------------------------
// Feature mutations
// ---------------------------------------------------------------------------

export function useCreateFeature() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateFeatureRequest) => api.createFeature(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: BOARD_KEY }),
  });
}

export function useUpdateFeatureMetadata() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateFeatureMetadataRequest }) =>
      api.updateFeatureMetadata(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: BOARD_KEY }),
  });
}

export function useDeleteFeature() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteFeature(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: BOARD_KEY }),
  });
}

export function useSuspendFeature() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.suspendFeature(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: BOARD_KEY }),
  });
}

export function useResumeFeature() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.resumeFeature(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: BOARD_KEY }),
  });
}

// ---------------------------------------------------------------------------
// Backlog mutations
// ---------------------------------------------------------------------------

export function useActivateBacklogFeature() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.activateBacklogFeature(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: BOARD_KEY }),
  });
}

// ---------------------------------------------------------------------------
// Task mutations
// ---------------------------------------------------------------------------

export function useCreateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ featureId, data }: { featureId: string; data: CreateTaskRequest }) =>
      api.createTask(featureId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: BOARD_KEY }),
  });
}

export function useUpdateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      featureId,
      taskId,
      data,
    }: {
      featureId: string;
      taskId: string;
      data: UpdateTaskRequest;
    }) => api.updateTask(featureId, taskId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: BOARD_KEY }),
  });
}

export function useMoveTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      featureId,
      taskId,
      data,
    }: {
      featureId: string;
      taskId: string;
      data: MoveTaskRequest;
    }) => api.moveTask(featureId, taskId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: BOARD_KEY }),
  });
}

export function useDeleteTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ featureId, taskId }: { featureId: string; taskId: string }) =>
      api.deleteTask(featureId, taskId),
    onSuccess: () => qc.invalidateQueries({ queryKey: BOARD_KEY }),
  });
}
