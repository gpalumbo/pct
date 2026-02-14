import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as api from '../api/configApi';
import type {
  AgentConfig,
  LoRARegistryEntry,
  ModelRegistryEntry,
  ProjectConfig,
  WorkflowStageConfig,
} from '../types/config';

// ---------------------------------------------------------------------------
// Model Registry
// ---------------------------------------------------------------------------

export function useModels() {
  return useQuery({ queryKey: ['models'], queryFn: api.fetchModels });
}

export function useCreateModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ModelRegistryEntry) => api.createModel(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['models'] }),
  });
}

export function useUpdateModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ModelRegistryEntry }) =>
      api.updateModel(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['models'] }),
  });
}

export function useDeleteModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteModel(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['models'] }),
  });
}

// ---------------------------------------------------------------------------
// LoRA Registry
// ---------------------------------------------------------------------------

export function useLoras() {
  return useQuery({ queryKey: ['loras'], queryFn: api.fetchLoras });
}

export function useCreateLora() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: LoRARegistryEntry) => api.createLora(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['loras'] }),
  });
}

export function useUpdateLora() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: LoRARegistryEntry }) =>
      api.updateLora(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['loras'] }),
  });
}

export function useDeleteLora() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteLora(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['loras'] }),
  });
}

// ---------------------------------------------------------------------------
// Agents
// ---------------------------------------------------------------------------

export function useAgents() {
  return useQuery({ queryKey: ['agents'], queryFn: api.fetchAgents });
}

export function useCreateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AgentConfig) => api.createAgent(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agents'] }),
  });
}

export function useUpdateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AgentConfig }) =>
      api.updateAgent(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agents'] }),
  });
}

export function useDeleteAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteAgent(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agents'] }),
  });
}

// ---------------------------------------------------------------------------
// Workflow Stages
// ---------------------------------------------------------------------------

export function useWorkflowStages() {
  return useQuery({ queryKey: ['workflow-stages'], queryFn: api.fetchWorkflowStages });
}

export function useSaveWorkflowStages() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: WorkflowStageConfig[]) => api.saveWorkflowStages(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workflow-stages'] }),
  });
}

// ---------------------------------------------------------------------------
// Project Config
// ---------------------------------------------------------------------------

export function useProjectConfig() {
  return useQuery({ queryKey: ['project-config'], queryFn: api.fetchProjectConfig });
}

export function useSaveProjectConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ProjectConfig) => api.saveProjectConfig(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['project-config'] });
      qc.invalidateQueries({ queryKey: ['agents'] });
      qc.invalidateQueries({ queryKey: ['workflow-stages'] });
    },
  });
}
