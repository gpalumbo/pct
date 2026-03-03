/** Config API wrapper. */

import client from './client';
import type { FileEntry, ModelRegistryEntry, Project, ProjectStatus } from '../types/config';

export const configApi = {
  getProjectStatus: () =>
    client.get<ProjectStatus>('/api/config/project/status').then((r) => r.data),

  getProject: () => client.get<Project>('/api/config/project').then((r) => r.data),

  updateProject: (project: Project) => {
    // Strip 'initialized' — added by GET response but not part of backend model (extra=forbid)
    const { initialized: _, ...payload } = project;
    return client.put<Project>('/api/config/project', payload).then((r) => r.data);
  },

  initializeProject: (name: string, projectType: string) =>
    client
      .post<Project>('/api/config/project/initialize', { name, project_type: projectType })
      .then((r) => r.data),

  browseFiles: (path?: string) =>
    client.get<FileEntry[]>('/api/config/browse-files', { params: { path } }).then((r) => r.data),

  register: (email: string, password: string) =>
    client.post<{ access_token: string }>('/api/auth/register', { email, password }).then((r) => r.data),

  login: (email: string, password: string) =>
    client.post<{ access_token: string }>('/api/auth/login', { email, password }).then((r) => r.data),

  getMe: () => client.get<{ email: string }>('/api/auth/me').then((r) => r.data),

  // Model registry
  getModels: () => client.get<ModelRegistryEntry[]>('/api/config/models').then((r) => r.data),

  createModel: (data: Omit<ModelRegistryEntry, 'id'>) =>
    client.post<ModelRegistryEntry>('/api/config/models', data).then((r) => r.data),

  updateModel: (id: string, data: Partial<Omit<ModelRegistryEntry, 'id'>>) =>
    client.put<ModelRegistryEntry>(`/api/config/models/${id}`, data).then((r) => r.data),

  deleteModel: (id: string) => client.delete(`/api/config/models/${id}`),
};
