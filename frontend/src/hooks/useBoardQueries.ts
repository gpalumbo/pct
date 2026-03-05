/** TanStack Query hooks for board API. */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { boardApi } from '../api/boardApi';
import type { BoardState, Feature, FeatureCreate, TaskCreate, TaskMove, TaskUpdate } from '../types/board';

export function useBoardQuery() {
  return useQuery({
    queryKey: ['board'],
    queryFn: boardApi.getBoard,
    staleTime: 5000,
    refetchInterval: 10_000,
  });
}

export function useCreateFeature() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: FeatureCreate) => boardApi.createFeature(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['board'] }),
  });
}

export function useCreateTask(featureId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TaskCreate) => boardApi.createTask(featureId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['board'] }),
  });
}

export function useMoveTask(featureId: string, taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TaskMove) => boardApi.moveTask(featureId, taskId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['board'] }),
  });
}

/** Flexible move hook with optimistic update — accepts featureId/taskId at call time (for drag-and-drop). */
export function useMoveTaskDynamic() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ featureId, taskId, data }: { featureId: string; taskId: string; data: TaskMove }) =>
      boardApi.moveTask(featureId, taskId, data),
    onMutate: async ({ featureId, taskId, data }) => {
      // Cancel any in-flight board fetches so they don't overwrite our optimistic update
      await qc.cancelQueries({ queryKey: ['board'] });
      const previous = qc.getQueryData<BoardState>(['board']);
      // Optimistically move the task to the new stage
      qc.setQueryData<BoardState>(['board'], (old) => {
        if (!old) return old;
        return {
          ...old,
          features: old.features.map((f) =>
            f.id === featureId
              ? {
                  ...f,
                  tasks: f.tasks.map((t) =>
                    t.id === taskId ? { ...t, current_stage_id: data.target_stage_id } : t,
                  ),
                }
              : f,
          ),
        };
      });
      return { previous };
    },
    onError: (_err, _vars, context) => {
      // Roll back to previous state on failure
      if (context?.previous) {
        qc.setQueryData(['board'], context.previous);
      }
    },
    onSettled: () => {
      // Always refetch to sync with server truth
      qc.invalidateQueries({ queryKey: ['board'] });
    },
  });
}

export function useUpdateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ featureId, taskId, data }: { featureId: string; taskId: string; data: TaskUpdate }) =>
      boardApi.updateTask(featureId, taskId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['board'] }),
  });
}

/** Feature update (stage, title, etc). */
export function useUpdateFeature() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ featureId, data }: { featureId: string; data: Partial<Feature> }) =>
      boardApi.updateFeature(featureId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['board'] }),
  });
}

/** Save artifact content with proper cache invalidation. */
export function useSaveArtifact() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ featureId, taskId, content }: { featureId: string; taskId: string; content: string }) =>
      boardApi.putArtifact(featureId, taskId, content),
    onSuccess: (_data, { featureId, taskId }) => {
      qc.invalidateQueries({ queryKey: ['artifact', featureId, taskId] });
    },
  });
}

export function useArtifact(featureId: string, taskId: string) {
  return useQuery({
    queryKey: ['artifact', featureId, taskId],
    queryFn: () => boardApi.getArtifact(featureId, taskId),
    enabled: !!featureId && !!taskId,
  });
}

export function useFeaturePert(featureId: string | null) {
  return useQuery({
    queryKey: ['pert', 'feature', featureId],
    queryFn: () => boardApi.getFeaturePert(featureId!),
    enabled: featureId !== null,
    staleTime: 10000,
  });
}

export function useProjectPert() {
  return useQuery({
    queryKey: ['pert', 'project'],
    queryFn: boardApi.getProjectPert,
    staleTime: 10000,
  });
}
