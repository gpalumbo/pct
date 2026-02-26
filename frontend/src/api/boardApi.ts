import client from './client';
import { useAuthStore } from '../stores/authStore';
import type {
  BacklogFeature,
  BoardResponse,
  CreateFeatureRequest,
  CreateTaskRequest,
  Feature,
  MoveTaskRequest,
  ReassignTaskRequest,
  Task,
  UpdateFeatureMetadataRequest,
  UpdateTaskRequest,
} from '../types/board';

// Composite board
export const fetchBoard = () => client.get<BoardResponse>('/api/board/').then((r) => r.data);

// Features
export const fetchFeatures = () => client.get<Feature[]>('/api/board/features').then((r) => r.data);
export const fetchFeature = (id: string) =>
  client.get<Feature>(`/api/board/features/${id}`).then((r) => r.data);
export const createFeature = (data: CreateFeatureRequest) =>
  client.post<Feature>('/api/board/features', data).then((r) => r.data);
export const updateFeatureMetadata = (id: string, data: UpdateFeatureMetadataRequest) =>
  client.patch<Feature>(`/api/board/features/${id}`, data).then((r) => r.data);
export const deleteFeature = (id: string) => client.delete(`/api/board/features/${id}`);
export const suspendFeature = (id: string) =>
  client.post<Feature>(`/api/board/features/${id}/suspend`).then((r) => r.data);
export const resumeFeature = (id: string) =>
  client.post<Feature>(`/api/board/features/${id}/resume`).then((r) => r.data);

// Backlog
export const fetchBacklog = () =>
  client.get<BacklogFeature[]>('/api/board/backlog').then((r) => r.data);
export const activateBacklogFeature = (id: string) =>
  client.post<Feature>(`/api/board/backlog/${id}/activate`).then((r) => r.data);

// Tasks
export const fetchTasks = (featureId: string) =>
  client.get<Task[]>(`/api/board/features/${featureId}/tasks`).then((r) => r.data);
export const fetchTask = (featureId: string, taskId: string) =>
  client.get<Task>(`/api/board/features/${featureId}/tasks/${taskId}`).then((r) => r.data);
export const createTask = (featureId: string, data: CreateTaskRequest) =>
  client.post<Task>(`/api/board/features/${featureId}/tasks`, data).then((r) => r.data);
export const updateTask = (featureId: string, taskId: string, data: UpdateTaskRequest) =>
  client.put<Task>(`/api/board/features/${featureId}/tasks/${taskId}`, data).then((r) => r.data);
export const moveTask = (featureId: string, taskId: string, data: MoveTaskRequest) =>
  client
    .post<Task>(`/api/board/features/${featureId}/tasks/${taskId}/move`, data)
    .then((r) => r.data);
export const deleteTask = (featureId: string, taskId: string) =>
  client.delete(`/api/board/features/${featureId}/tasks/${taskId}`);
export const reassignTask = (data: ReassignTaskRequest) =>
  client.post<Task>('/api/board/tasks/reassign', data).then((r) => r.data);

// Artifacts
export interface ArtifactResponse {
  path: string;
  content: string;
  exists: boolean;
}

export const fetchArtifact = (featureId: string, taskId: string) =>
  client
    .get<ArtifactResponse>(`/api/board/features/${featureId}/tasks/${taskId}/artifact`)
    .then((r) => r.data);

export const saveArtifact = (featureId: string, taskId: string, content: string) =>
  client
    .put<ArtifactResponse>(`/api/board/features/${featureId}/tasks/${taskId}/artifact`, { content })
    .then((r) => r.data);

// Artifact files (directory listing)
export interface ArtifactFile {
  path: string;
  name: string;
  size: number;
  is_image: boolean;
}

export const fetchArtifactFiles = (featureId: string, taskId: string) =>
  client
    .get<ArtifactFile[]>(`/api/board/features/${featureId}/tasks/${taskId}/files`)
    .then((r) => r.data);

// Artifact types
export const fetchArtifactTypes = () =>
  client.get<Record<string, string>>('/api/board/artifact-types').then((r) => r.data);

// Analysis SSE streaming
function streamAnalysis(
  url: string,
  onToken: (token: string) => void,
  onDone: (content: string) => void,
  onError: (error: string) => void,
): AbortController {
  const controller = new AbortController();
  const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const token = useAuthStore.getState().token;

  fetch(`${baseURL}${url}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        onError(`HTTP ${response.status}: ${response.statusText}`);
        return;
      }
      const reader = response.body?.getReader();
      if (!reader) {
        onError('No response body');
        return;
      }
      const decoder = new TextDecoder();
      let buffer = '';

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if ('token' in event) {
              onToken(event.token);
            } else if ('done' in event) {
              onDone(event.content || '');
            } else if ('error' in event) {
              onError(event.error);
            }
          } catch {
            // skip malformed lines
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError(err.message || 'Stream failed');
      }
    });

  return controller;
}

export function runGapAnalysis(
  featureId: string,
  onToken: (token: string) => void,
  onDone: (content: string) => void,
  onError: (error: string) => void,
): AbortController {
  return streamAnalysis(`/api/board/features/${featureId}/gap-analysis`, onToken, onDone, onError);
}

export function runContinuityCheck(
  featureId: string,
  onToken: (token: string) => void,
  onDone: (content: string) => void,
  onError: (error: string) => void,
): AbortController {
  return streamAnalysis(
    `/api/board/features/${featureId}/continuity-check`,
    onToken,
    onDone,
    onError,
  );
}
