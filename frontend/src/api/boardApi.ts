import client from './client';
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
export const fetchBoard = () =>
  client.get<BoardResponse>('/api/board/').then((r) => r.data);

// Features
export const fetchFeatures = () =>
  client.get<Feature[]>('/api/board/features').then((r) => r.data);
export const fetchFeature = (id: string) =>
  client.get<Feature>(`/api/board/features/${id}`).then((r) => r.data);
export const createFeature = (data: CreateFeatureRequest) =>
  client.post<Feature>('/api/board/features', data).then((r) => r.data);
export const updateFeatureMetadata = (id: string, data: UpdateFeatureMetadataRequest) =>
  client.patch<Feature>(`/api/board/features/${id}`, data).then((r) => r.data);
export const deleteFeature = (id: string) =>
  client.delete(`/api/board/features/${id}`);
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
  client.post<Task>(`/api/board/features/${featureId}/tasks/${taskId}/move`, data).then((r) => r.data);
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
  client.get<ArtifactResponse>(`/api/board/features/${featureId}/tasks/${taskId}/artifact`).then((r) => r.data);

export const saveArtifact = (featureId: string, taskId: string, content: string) =>
  client.put<ArtifactResponse>(`/api/board/features/${featureId}/tasks/${taskId}/artifact`, { content }).then((r) => r.data);
