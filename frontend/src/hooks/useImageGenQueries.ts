/** TanStack Query hooks for image generation API. */

import { useQuery, useMutation } from '@tanstack/react-query';
import { imagegenApi, type GenerateRequest } from '../api/imagegenApi';

export function useImageSession(featureId: string, taskId: string) {
  return useQuery({
    queryKey: ['imagegen', featureId, taskId],
    queryFn: () => imagegenApi.getSession(featureId, taskId),
    enabled: !!featureId && !!taskId,
  });
}

export function useGenerate() {
  return useMutation({
    mutationFn: (data: GenerateRequest) => imagegenApi.generate(data),
  });
}
