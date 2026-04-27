/** Image generation API wrapper. */

import client from './client';
import { connectSSE } from './sseStream';

export interface GenerateRequest {
  feature_id: string;
  task_id: string;
  prompt: string;
  negative_prompt?: string;
  guidance_scale?: number;
  num_images?: number;
  divergence?: number;
  source_image_id?: string;
  width?: number;
  height?: number;
  model_id?: string;
  draft?: boolean;
}

export interface ResolutionOption {
  label: string;
  width: number;
  height: number;
}

export interface TaskImage {
  id: string;
  task_id: string;
  feature_id: string;
  filename: string;
  url: string;
  created_at: number;
}

export interface FeatureImage {
  id: string;
  task_id: string;
  feature_id: string;
  filename: string;
  url: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: string;
  status_message?: string;
  feature_id?: string;
  task_id?: string;
  images: Array<{ id?: string; image_id?: string }>;
  error?: string;
  model_id?: string;
  preview?: { preview_id: string; index: number };
}

export interface ImagegenModel {
  id: string;
  name: string;
  architecture?: string;
  download_status?: string;
  native_resolution?: number;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function getImageUrl(featureId: string, taskId: string, imageId: string): string {
  return `${API_BASE_URL}/api/imagegen/images/${featureId}/${taskId}/${imageId}`;
}

export const imagegenApi = {
  generate: (data: GenerateRequest) =>
    client.post<{ job_id: string }>('/api/imagegen/generate', data).then((r) => r.data),

  getResolutions: (architecture?: string, nativeResolution?: number) =>
    client
      .get<{ resolutions: ResolutionOption[] }>('/api/imagegen/resolutions', {
        params: {
          ...(architecture ? { architecture } : {}),
          ...(nativeResolution ? { native_resolution: nativeResolution } : {}),
        },
      })
      .then((r) => r.data.resolutions),

  listModels: () =>
    client
      .get<{ models: ImagegenModel[] }>('/api/imagegen/models')
      .then((r) => r.data.models),

  getJobStatus: (jobId: string) =>
    client.get<JobStatusResponse>(`/api/imagegen/jobs/${jobId}`).then((r) => r.data),

  getSession: (featureId: string, taskId: string) =>
    client.get(`/api/imagegen/${featureId}/${taskId}/session`).then((r) => r.data),

  selectImage: (featureId: string, taskId: string, imageId: string) =>
    client.post(`/api/imagegen/${featureId}/${taskId}/select`, { image_id: imageId }),

  listFeatureImages: (featureId: string) =>
    client
      .get<{ images: FeatureImage[] }>(`/api/imagegen/features/${featureId}/images`)
      .then((r) => r.data.images),

  listTaskImages: (featureId: string, taskId: string) =>
    client
      .get<{ images: TaskImage[] }>(`/api/imagegen/${featureId}/${taskId}/images`)
      .then((r) => r.data.images),

  deleteImage: (featureId: string, taskId: string, imageId: string) =>
    client.delete(`/api/imagegen/${featureId}/${taskId}/images/${imageId}`).then((r) => r.data),

  cancelJob: (jobId: string) =>
    client.post(`/api/imagegen/jobs/${jobId}/cancel`).then((r) => r.data),

  listJobs: (featureId: string, taskId: string) =>
    client
      .get<JobStatusResponse[]>('/api/imagegen/jobs', {
        params: { feature_id: featureId, task_id: taskId },
      })
      .then((r) => r.data),

  streamJobStatus: (
    jobId: string,
    onEvent: (event: Record<string, unknown>) => void,
    onError?: (error: string) => void,
  ) =>
    connectSSE({
      url: `${API_BASE_URL}/api/imagegen/jobs/${jobId}/stream`,
      onEvent,
      onError,
    }),
};
