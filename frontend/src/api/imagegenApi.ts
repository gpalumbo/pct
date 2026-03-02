/** Image generation API wrapper. */

import client from './client';

export interface GenerateRequest {
  feature_id: string;
  task_id: string;
  prompt: string;
  negative_prompt?: string;
  guidance_scale?: number;
  divergence?: number;
  source_image_id?: string;
}

export const imagegenApi = {
  generate: (data: GenerateRequest) =>
    client.post<{ job_id: string }>('/api/imagegen/generate', data).then((r) => r.data),

  getJobStatus: (jobId: string) =>
    client.get<{ status: string; progress?: number }>(`/api/imagegen/jobs/${jobId}`).then((r) => r.data),

  getSession: (featureId: string, taskId: string) =>
    client.get(`/api/imagegen/${featureId}/${taskId}/session`).then((r) => r.data),

  selectImage: (featureId: string, taskId: string, imageId: string) =>
    client.post(`/api/imagegen/${featureId}/${taskId}/select`, { image_id: imageId }),
};
