/** Shared chat state hook — used by PlanningChat and TaskDetailPanel. */

import { useState, useCallback } from 'react';
import { chatApi } from '../api/chatApi';
import type { ChatMessage, SSEEvent } from '../types/chat';

interface UsePlanningChatOptions {
  sessionId: string;
  initialMessages?: ChatMessage[];
}

export function usePlanningChat({ sessionId, initialMessages = [] }: UsePlanningChatOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamContent, setStreamContent] = useState('');
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);

  const refreshMessages = useCallback(async () => {
    const msgs = await chatApi.getMessages(sessionId);
    setMessages(msgs);
  }, [sessionId]);

  const sendMessage = useCallback(
    async (content: string) => {
      setIsStreaming(true);
      setStreamContent('');

      try {
        await chatApi.sendMessage(sessionId, content, selectedAgentId, (event: SSEEvent) => {
          if (event.type === 'token' && event.content) {
            setStreamContent((prev) => prev + event.content);
          } else if (event.type === 'done') {
            setIsStreaming(false);
            refreshMessages();
          } else if (event.type === 'error') {
            setIsStreaming(false);
          }
        });
      } catch {
        setIsStreaming(false);
      }
    },
    [sessionId, selectedAgentId, refreshMessages],
  );

  const toggleIncluded = useCallback(
    async (messageId: string, included: boolean) => {
      await chatApi.updateMessage(sessionId, messageId, { included });
      await refreshMessages();
    },
    [sessionId, refreshMessages],
  );

  const deleteMessage = useCallback(
    async (messageId: string) => {
      await chatApi.deleteMessage(sessionId, messageId);
      await refreshMessages();
    },
    [sessionId, refreshMessages],
  );

  return {
    messages,
    isStreaming,
    streamContent,
    selectedAgentId,
    setSelectedAgentId,
    sendMessage,
    refreshMessages,
    toggleIncluded,
    deleteMessage,
  };
}
