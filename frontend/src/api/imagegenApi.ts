import client from './client';

// Types matching backend models
export interface GeneratedImage {
  filename: string;
  seed: number;
  round: number;
  index: number;
}

export interface JobResponse {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  images: GeneratedImage[];
  error: string | null;
}

export interface GenerationRound {
  round: number;
  prompt: string;
  params: Record<string, unknown>;
  images: GeneratedImage[];
  selected_image: string | null;
}

export interface SessionMetadata {
  feature_id: string;
  task_id: string;
  model_id: string;
  rounds: GenerationRound[];
  current_round: number;
}

export interface GenerateRequest {
  feature_id: string;
  task_id: string;
  prompt: string;
  negative_prompt?: string;
  guidance_scale?: number;
  num_inference_steps?: number;
  width?: number;
  height?: number;
  source_image?: string | null;
  divergence?: number;
  seed?: number | null;
}

export interface SelectImageRequest {
  round: number;
  filename: string;
}

export const startGeneration = (data: GenerateRequest) =>
  client.post<{ job_id: string }>('/api/imagegen/generate', data).then((r) => r.data);

export const fetchJobStatus = (jobId: string) =>
  client.get<JobResponse>(`/api/imagegen/jobs/${jobId}`).then((r) => r.data);

export const fetchSession = (featureId: string, taskId: string) =>
  client.get<SessionMetadata>(`/api/imagegen/${featureId}/${taskId}/session`).then((r) => r.data);

export const selectImage = (featureId: string, taskId: string, data: SelectImageRequest) =>
  client
    .post<SessionMetadata>(`/api/imagegen/${featureId}/${taskId}/select`, data)
    .then((r) => r.data);

export const getImageUrl = (featureId: string, taskId: string, filename: string) =>
  `/api/imagegen/${featureId}/${taskId}/images/${filename}`;

export const fetchImageBlob = (featureId: string, taskId: string, filename: string) =>
  client
    .get(`/api/imagegen/${featureId}/${taskId}/images/${filename}`, { responseType: 'blob' })
    .then((r) => r.data as Blob);
