/** TanStack Query hooks for image generation API. */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { imagegenApi, type GenerateRequest } from '../api/imagegenApi';

export function useImageSession(featureId: string, taskId: string) {
  return useQuery({
    queryKey: ['imagegen', featureId, taskId],
    queryFn: () => imagegenApi.getSession(featureId, taskId),
    enabled: !!featureId && !!taskId,
  });
}

export function useFeatureImages(featureId: string) {
  return useQuery({
    queryKey: ['imagegen', 'feature-images', featureId],
    queryFn: () => imagegenApi.listFeatureImages(featureId),
    enabled: !!featureId,
  });
}

export function useTaskImages(featureId: string, taskId: string) {
  return useQuery({
    queryKey: ['imagegen', 'task-images', featureId, taskId],
    queryFn: () => imagegenApi.listTaskImages(featureId, taskId),
    enabled: !!featureId && !!taskId,
  });
}

export function useGenerate() {
  return useMutation({
    mutationFn: (data: GenerateRequest) => imagegenApi.generate(data),
  });
}

export function useDeleteImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ featureId, taskId, imageId }: { featureId: string; taskId: string; imageId: string }) =>
      imagegenApi.deleteImage(featureId, taskId, imageId),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['imagegen', 'task-images', vars.featureId, vars.taskId] });
    },
  });
}

export function useCancelJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => imagegenApi.cancelJob(jobId),
    onSuccess: (_data, jobId) => {
      qc.invalidateQueries({ queryKey: ['imagegen', 'job', jobId] });
    },
  });
}

export function useJobStatus(jobId: string | null) {
  return useQuery({
    queryKey: ['imagegen', 'job', jobId],
    queryFn: () => imagegenApi.getJobStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed') return false;
      return 1500;
    },
  });
}
