import client from './client';
import type {
  AgentConfig,
  ArtifactTypeConfig,
  LoRARegistryEntry,
  ModelRegistryEntry,
  ProjectConfig,
  ProjectStatus,
  TemplateVariable,
  WorkflowStageConfig,
} from '../types/config';

// File Browser
export interface FileEntry {
  name: string;
  path: string;
  is_dir: boolean;
}
export const browseFiles = (path: string = '') =>
  client.get<FileEntry[]>('/api/config/browse-files', { params: { path } }).then((r) => r.data);

// Model Registry
export const fetchModels = () =>
  client.get<ModelRegistryEntry[]>('/api/config/models').then((r) => r.data);
export const fetchModel = (id: string) =>
  client.get<ModelRegistryEntry>(`/api/config/models/${id}`).then((r) => r.data);
export const createModel = (data: ModelRegistryEntry) =>
  client.post<ModelRegistryEntry>('/api/config/models', data).then((r) => r.data);
export const updateModel = (id: string, data: ModelRegistryEntry) =>
  client.put<ModelRegistryEntry>(`/api/config/models/${id}`, data).then((r) => r.data);
export const deleteModel = (id: string) => client.delete(`/api/config/models/${id}`);

// LoRA Registry
export const fetchLoras = () =>
  client.get<LoRARegistryEntry[]>('/api/config/loras').then((r) => r.data);
export const fetchLora = (id: string) =>
  client.get<LoRARegistryEntry>(`/api/config/loras/${id}`).then((r) => r.data);
export const createLora = (data: LoRARegistryEntry) =>
  client.post<LoRARegistryEntry>('/api/config/loras', data).then((r) => r.data);
export const updateLora = (id: string, data: LoRARegistryEntry) =>
  client.put<LoRARegistryEntry>(`/api/config/loras/${id}`, data).then((r) => r.data);
export const deleteLora = (id: string) => client.delete(`/api/config/loras/${id}`);

// Project Config
export const fetchProjectStatus = () =>
  client.get<ProjectStatus>('/api/config/project/status').then((r) => r.data);
export const fetchProjectConfig = () =>
  client.get<ProjectConfig | null>('/api/config/project').then((r) => r.data);
export const saveProjectConfig = (data: ProjectConfig) =>
  client.put<ProjectConfig>('/api/config/project', data).then((r) => r.data);

// Agents
export const fetchAgents = () =>
  client.get<AgentConfig[]>('/api/config/agents').then((r) => r.data);
export const fetchAgent = (id: string) =>
  client.get<AgentConfig>(`/api/config/agents/${id}`).then((r) => r.data);
export const createAgent = (data: AgentConfig) =>
  client.post<AgentConfig>('/api/config/agents', data).then((r) => r.data);
export const updateAgent = (id: string, data: AgentConfig) =>
  client.put<AgentConfig>(`/api/config/agents/${id}`, data).then((r) => r.data);
export const deleteAgent = (id: string) => client.delete(`/api/config/agents/${id}`);

// Reindex
export interface ReindexResponse {
  indexed: number;
  error?: string;
}
export const reindexProject = () =>
  client.post<ReindexResponse>('/api/config/project/reindex').then((r) => r.data);

// Workflow Stages
export const fetchWorkflowStages = () =>
  client.get<WorkflowStageConfig[]>('/api/config/workflow-stages').then((r) => r.data);
export const saveWorkflowStages = (data: WorkflowStageConfig[]) =>
  client.put<WorkflowStageConfig[]>('/api/config/workflow-stages', data).then((r) => r.data);

// Template Variables
export const fetchTemplateVariables = () =>
  client.get<TemplateVariable[]>('/api/config/template-variables').then((r) => r.data);
export const saveTemplateVariables = (data: TemplateVariable[]) =>
  client.put<TemplateVariable[]>('/api/config/template-variables', data).then((r) => r.data);

// Artifact Types
export const fetchArtifactTypes = () =>
  client.get<ArtifactTypeConfig[]>('/api/config/artifact-types').then((r) => r.data);
export const saveArtifactTypes = (data: ArtifactTypeConfig[]) =>
  client.put<ArtifactTypeConfig[]>('/api/config/artifact-types', data).then((r) => r.data);
