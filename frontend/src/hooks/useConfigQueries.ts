/** TanStack Query hooks for config API. */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { configApi } from '../api/configApi';
import type { LoRARegistryEntry, ModelRegistryEntry, Project } from '../types/config';

export function useProjectStatus() {
  return useQuery({
    queryKey: ['projectStatus'],
    queryFn: configApi.getProjectStatus,
    staleTime: 10000,
  });
}

export function useProject() {
  return useQuery({
    queryKey: ['project'],
    queryFn: configApi.getProject,
    staleTime: 5000,
  });
}

export function useUpdateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (project: Project) => configApi.updateProject(project),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['project'] }),
  });
}

export function useInitializeProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, projectType }: { name: string; projectType: string }) =>
      configApi.initializeProject(name, projectType),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['project'] });
      qc.invalidateQueries({ queryKey: ['projectStatus'] });
    },
  });
}

export function useBrowseFiles(path?: string) {
  return useQuery({
    queryKey: ['files', path],
    queryFn: () => configApi.browseFiles(path),
    enabled: path !== undefined,
  });
}

// ── Model registry hooks ────────────────────────────────────────

export function useModels() {
  return useQuery({
    queryKey: ['models'],
    queryFn: configApi.getModels,
    staleTime: 5000,
  });
}

export function useCreateModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Omit<ModelRegistryEntry, 'id'>) => configApi.createModel(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['models'] }),
  });
}

export function useUpdateModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Omit<ModelRegistryEntry, 'id'>> }) =>
      configApi.updateModel(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['models'] }),
  });
}

export function useDeleteModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => configApi.deleteModel(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['models'] }),
  });
}

// ── LoRA registry hooks ─────────────────────────────────────────

export function useLoras() {
  return useQuery({
    queryKey: ['loras'],
    queryFn: configApi.getLoras,
    staleTime: 5000,
  });
}

export function useCreateLora() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Omit<LoRARegistryEntry, 'id' | 'versions'>) => configApi.createLora(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['loras'] }),
  });
}

export function useUpdateLora() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Omit<LoRARegistryEntry, 'id' | 'versions'>> }) =>
      configApi.updateLora(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['loras'] }),
  });
}

export function useDeleteLora() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => configApi.deleteLora(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['loras'] }),
  });
}

export function useAddLoraVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ loraId, data }: { loraId: string; data: { file_path: string; training_job_id?: string | null } }) =>
      configApi.addLoraVersion(loraId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['loras'] }),
  });
}
