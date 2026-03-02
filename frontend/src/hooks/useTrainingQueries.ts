/** TanStack Query hooks for training API. */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { trainingApi } from '../api/trainingApi';
import type {
  FlagCreate,
  FlagUpdate,
  DatasetCreate,
  DatasetUpdate,
  PromptTemplateCreate,
  PromptTemplateUpdate,
} from '../types/training';

// ---- Flags ----

export function useFlags(params?: { flag_type?: string; status?: string }) {
  return useQuery({
    queryKey: ['training-flags', params],
    queryFn: () => trainingApi.listFlags(params),
    staleTime: 5000,
  });
}

export function useFlag(id: string | null) {
  return useQuery({
    queryKey: ['training-flag', id],
    queryFn: () => trainingApi.getFlag(id!),
    enabled: id !== null,
    staleTime: 5000,
  });
}

export function useCreateFlagMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: FlagCreate) => trainingApi.createFlag(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['training-flags'] }),
  });
}

export function useUpdateFlagMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: FlagUpdate }) =>
      trainingApi.updateFlag(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['training-flags'] });
      qc.invalidateQueries({ queryKey: ['training-flag'] });
    },
  });
}

export function useDeleteFlagMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => trainingApi.deleteFlag(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['training-flags'] }),
  });
}

// ---- Datasets ----

export function useDatasets() {
  return useQuery({
    queryKey: ['training-datasets'],
    queryFn: trainingApi.listDatasets,
    staleTime: 5000,
  });
}

export function useDataset(id: string | null) {
  return useQuery({
    queryKey: ['training-dataset', id],
    queryFn: () => trainingApi.getDataset(id!),
    enabled: id !== null,
    staleTime: 5000,
  });
}

export function useCreateDatasetMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: DatasetCreate) => trainingApi.createDataset(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['training-datasets'] }),
  });
}

export function useUpdateDatasetMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DatasetUpdate }) =>
      trainingApi.updateDataset(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['training-datasets'] });
      qc.invalidateQueries({ queryKey: ['training-dataset'] });
    },
  });
}

export function useDeleteDatasetMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => trainingApi.deleteDataset(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['training-datasets'] }),
  });
}

// ---- Prompt Templates ----

export function useTemplates() {
  return useQuery({
    queryKey: ['training-templates'],
    queryFn: trainingApi.listTemplates,
    staleTime: 5000,
  });
}

export function useTemplate(id: string | null) {
  return useQuery({
    queryKey: ['training-template', id],
    queryFn: () => trainingApi.getTemplate(id!),
    enabled: id !== null,
    staleTime: 5000,
  });
}

export function useCreateTemplateMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: PromptTemplateCreate) => trainingApi.createTemplate(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['training-templates'] }),
  });
}

export function useUpdateTemplateMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PromptTemplateUpdate }) =>
      trainingApi.updateTemplate(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['training-templates'] });
      qc.invalidateQueries({ queryKey: ['training-template'] });
    },
  });
}
