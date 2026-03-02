/** TanStack Query hooks for config API. */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { configApi } from '../api/configApi';
import type { Project } from '../types/config';

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
