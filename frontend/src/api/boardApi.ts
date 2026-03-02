/** Board API wrapper. */

import client from './client';
import type { BoardState, Feature, FeatureCreate, Task, TaskCreate, TaskMove } from '../types/board';
import type { PertData } from '../types/pert';

export const boardApi = {
  getBoard: () => client.get<BoardState>('/api/board/').then((r) => r.data),

  createFeature: (data: FeatureCreate) =>
    client.post<Feature>('/api/board/features', data).then((r) => r.data),

  getFeature: (id: string) =>
    client.get<Feature>(`/api/board/features/${id}`).then((r) => r.data),

  updateFeature: (id: string, data: Partial<Feature>) =>
    client.patch<Feature>(`/api/board/features/${id}`, data).then((r) => r.data),

  deleteFeature: (id: string) => client.delete(`/api/board/features/${id}`),

  suspendFeature: (id: string) =>
    client.post<Feature>(`/api/board/features/${id}/suspend`).then((r) => r.data),

  resumeFeature: (id: string) =>
    client.post<Feature>(`/api/board/features/${id}/resume`).then((r) => r.data),

  listTasks: (featureId: string) =>
    client.get<Task[]>(`/api/board/features/${featureId}/tasks`).then((r) => r.data),

  createTask: (featureId: string, data: TaskCreate) =>
    client.post<Task>(`/api/board/features/${featureId}/tasks`, data).then((r) => r.data),

  getTask: (featureId: string, taskId: string) =>
    client.get<Task>(`/api/board/features/${featureId}/tasks/${taskId}`).then((r) => r.data),

  moveTask: (featureId: string, taskId: string, data: TaskMove) =>
    client.post<Task>(`/api/board/features/${featureId}/tasks/${taskId}/move`, data).then((r) => r.data),

  deleteTask: (featureId: string, taskId: string) =>
    client.delete(`/api/board/features/${featureId}/tasks/${taskId}`),

  getArtifact: (featureId: string, taskId: string) =>
    client.get<{ content: string }>(`/api/board/features/${featureId}/tasks/${taskId}/artifact`).then((r) => r.data),

  putArtifact: (featureId: string, taskId: string, content: string) =>
    client.put(`/api/board/features/${featureId}/tasks/${taskId}/artifact`, { content }),

  getFeaturePert: (featureId: string) =>
    client.get<PertData>(`/api/board/features/${featureId}/pert`).then((r) => r.data),

  getProjectPert: () =>
    client.get<PertData>('/api/board/pert').then((r) => r.data),
};
