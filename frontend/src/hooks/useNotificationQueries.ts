/** TanStack Query hooks for notifications API. */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notificationsApi } from '../api/notificationsApi';

const NOTIFICATION_KEYS = {
  all: ['notifications'] as const,
  list: ['notifications', 'list'] as const,
  badge: ['notifications', 'badge'] as const,
};

export function useNotifications() {
  return useQuery({
    queryKey: NOTIFICATION_KEYS.list,
    queryFn: () => notificationsApi.list(),
    refetchInterval: 30_000,
    staleTime: 10_000,
  });
}

export function useNotificationBadge() {
  return useQuery({
    queryKey: NOTIFICATION_KEYS.badge,
    queryFn: () => notificationsApi.badge(),
    refetchInterval: 30_000,
    staleTime: 10_000,
  });
}

export function useAcknowledgeMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (eventId: string) => notificationsApi.acknowledge(eventId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: NOTIFICATION_KEYS.all });
    },
  });
}

export function useAcknowledgeAllMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => notificationsApi.acknowledgeAll(),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: NOTIFICATION_KEYS.all });
    },
  });
}
