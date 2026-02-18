import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as api from '../api/chatApi';
import type { UpdateMessageRequest } from '../types/chat';

export function useDefaultSession() {
  return useQuery({ queryKey: ['chat-session-default'], queryFn: api.fetchDefaultSession });
}

export function useSession(sessionId: string | null) {
  return useQuery({
    queryKey: ['chat-session', sessionId],
    queryFn: () => api.fetchSession(sessionId!),
    enabled: !!sessionId,
    retry: false,
  });
}

export function useMessages(sessionId: string | null) {
  return useQuery({
    queryKey: ['chat-messages', sessionId],
    queryFn: () => api.fetchMessages(sessionId!),
    enabled: !!sessionId,
  });
}

export function useUpdateMessage(sessionId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ messageId, data }: { messageId: string; data: UpdateMessageRequest }) =>
      api.updateMessage(sessionId!, messageId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['chat-messages', sessionId] }),
  });
}

export function useDeleteMessage(sessionId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (messageId: string) => api.deleteMessage(sessionId!, messageId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['chat-messages', sessionId] }),
  });
}

export function useTruncateFromMessage(sessionId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (messageId: string) => api.truncateFromMessage(sessionId!, messageId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['chat-messages', sessionId] }),
  });
}
