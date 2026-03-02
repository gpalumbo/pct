/** TanStack Query hooks for board API. */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { boardApi } from '../api/boardApi';
import type { FeatureCreate, TaskCreate, TaskMove } from '../types/board';

export function useBoardQuery() {
  return useQuery({
    queryKey: ['board'],
    queryFn: boardApi.getBoard,
    staleTime: 5000,
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
