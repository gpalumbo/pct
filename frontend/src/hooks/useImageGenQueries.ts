/** TanStack Query hooks for image generation API. */

import { useEffect, useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { imagegenApi, type GenerateRequest, type JobStatusResponse } from '../api/imagegenApi';

export function useResolutions(architecture?: string, nativeResolution?: number) {
  return useQuery({
    queryKey: ['imagegen-resolutions', architecture, nativeResolution],
    queryFn: () => imagegenApi.getResolutions(architecture, nativeResolution),
    staleTime: Infinity,
  });
}

export function useImagegenModels() {
  return useQuery({
    queryKey: ['imagegen-models'],
    queryFn: () => imagegenApi.listModels(),
    staleTime: 30_000,
  });
}

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

export function useActiveJob(featureId: string, taskId: string) {
  return useQuery({
    queryKey: ['imagegen', 'active-job', featureId, taskId],
    queryFn: () => imagegenApi.listJobs(featureId, taskId),
    enabled: !!featureId && !!taskId,
    staleTime: 0,
    select: (jobs) => jobs[0] ?? null,
  });
}

export function useJobStatus(jobId: string | null) {
  const [status, setStatus] = useState<JobStatusResponse | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!jobId) {
      setStatus(null);
      return;
    }

    // Reset status when job changes
    setStatus(null);

    const controller = imagegenApi.streamJobStatus(
      jobId,
      (event) => {
        if ('image' in event) {
          // Progressive image — append to current status
          setStatus((prev) => {
            if (!prev) return prev;
            const img = event.image as { id?: string; image_id?: string };
            return { ...prev, images: [...prev.images, img] };
          });
        } else if ('done' in event) {
          // Job completed
          setStatus((prev) => ({
            ...(prev || { job_id: jobId }),
            job_id: prev?.job_id || jobId,
            status: 'completed',
            images: (event.images as Array<{ id?: string; image_id?: string }>) || prev?.images || [],
          }));
        } else if ('error' in event) {
          // Job failed
          setStatus((prev) => ({
            ...(prev || { job_id: jobId }),
            job_id: prev?.job_id || jobId,
            status: 'failed',
            error: event.error as string,
            images: prev?.images || [],
          }));
        } else if ('status' in event) {
          // Status transition (loading/running) or initial state
          setStatus((prev) => ({
            ...(prev || { job_id: jobId, images: [] }),
            job_id: prev?.job_id || jobId,
            status: event.status as string,
            status_message: (event.status_message as string) || undefined,
            images: (event.images as Array<{ id?: string; image_id?: string }>) || prev?.images || [],
          }));
        }
      },
      (error) => {
        setStatus((prev) => ({
          ...(prev || { job_id: jobId }),
          job_id: prev?.job_id || jobId,
          status: 'failed',
          error,
          images: prev?.images || [],
        }));
      },
    );

    controllerRef.current = controller;
    return () => controller.abort();
  }, [jobId]);

  return { data: status };
}
