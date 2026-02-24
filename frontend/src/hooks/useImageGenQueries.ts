import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as api from '../api/imagegenApi';

const SESSION_KEY = (featureId: string, taskId: string) =>
  ['imagegen-session', featureId, taskId] as const;

export function useImageGenSession(featureId: string, taskId: string) {
  return useQuery({
    queryKey: SESSION_KEY(featureId, taskId),
    queryFn: () => api.fetchSession(featureId, taskId),
    enabled: !!featureId && !!taskId,
  });
}

export function useJobStatus(jobId: string | null) {
  return useQuery({
    queryKey: ['imagegen-job', jobId],
    queryFn: () => api.fetchJobStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed') return false;
      return 1500;
    },
  });
}

export function useStartGeneration() {
  return useMutation({
    mutationFn: (data: api.GenerateRequest) => api.startGeneration(data),
  });
}

export function useSelectImage(featureId: string, taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: api.SelectImageRequest) => api.selectImage(featureId, taskId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: SESSION_KEY(featureId, taskId) }),
  });
}
