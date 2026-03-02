/** TanStack Query hooks for chat API. */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { chatApi } from '../api/chatApi';

export function useChatMessages(sessionId: string) {
  return useQuery({
    queryKey: ['chat', sessionId],
    queryFn: () => chatApi.getMessages(sessionId),
    staleTime: 2000,
    enabled: !!sessionId,
  });
}

export function useDefaultSession() {
  return useQuery({
    queryKey: ['chat', 'default'],
    queryFn: chatApi.getDefaultSession,
  });
}

export function useInvalidateChat() {
  const qc = useQueryClient();
  return (sessionId: string) => qc.invalidateQueries({ queryKey: ['chat', sessionId] });
}
