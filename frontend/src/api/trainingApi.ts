/** Training API wrapper. */

import client from './client';
import type {
  TrainingFlag,
  Dataset,
  PromptTemplate,
  FlagCreate,
  FlagUpdate,
  DatasetCreate,
  DatasetUpdate,
  PromptTemplateCreate,
  PromptTemplateUpdate,
} from '../types/training';

export const trainingApi = {
  // Flags
  createFlag: (data: FlagCreate) =>
    client.post<TrainingFlag>('/api/training/flags', data).then((r) => r.data),

  listFlags: (params?: { flag_type?: string; status?: string }) =>
    client.get<TrainingFlag[]>('/api/training/flags', { params }).then((r) => r.data),

  getFlag: (id: string) =>
    client.get<TrainingFlag>(`/api/training/flags/${id}`).then((r) => r.data),

  updateFlag: (id: string, data: FlagUpdate) =>
    client.put<TrainingFlag>(`/api/training/flags/${id}`, data).then((r) => r.data),

  deleteFlag: (id: string) => client.delete(`/api/training/flags/${id}`),

  // Datasets
  createDataset: (data: DatasetCreate) =>
    client.post<Dataset>('/api/training/datasets', data).then((r) => r.data),

  listDatasets: () =>
    client.get<Dataset[]>('/api/training/datasets').then((r) => r.data),

  getDataset: (id: string) =>
    client.get<Dataset>(`/api/training/datasets/${id}`).then((r) => r.data),

  updateDataset: (id: string, data: DatasetUpdate) =>
    client.put<Dataset>(`/api/training/datasets/${id}`, data).then((r) => r.data),

  deleteDataset: (id: string) => client.delete(`/api/training/datasets/${id}`),

  // Prompt Templates
  createTemplate: (data: PromptTemplateCreate) =>
    client.post<PromptTemplate>('/api/training/prompt-templates', data).then((r) => r.data),

  listTemplates: () =>
    client.get<PromptTemplate[]>('/api/training/prompt-templates').then((r) => r.data),

  getTemplate: (id: string) =>
    client.get<PromptTemplate>(`/api/training/prompt-templates/${id}`).then((r) => r.data),

  updateTemplate: (id: string, data: PromptTemplateUpdate) =>
    client.put<PromptTemplate>(`/api/training/prompt-templates/${id}`, data).then((r) => r.data),
};
