/** Chat API wrapper with SSE streaming support. */

import client from './client';
import type { ChatMessage, ChatSession, SSEEvent } from '../types/chat';

export const chatApi = {
  listSessions: () => client.get<ChatSession[]>('/api/chat/sessions').then((r) => r.data),

  getDefaultSession: () => client.get<ChatSession>('/api/chat/sessions/default').then((r) => r.data),

  getMessages: (sessionId: string) =>
    client.get<ChatMessage[]>(`/api/chat/sessions/${sessionId}/messages`).then((r) => r.data),

  /** Send a message and stream the response via SSE (using fetch for POST-based SSE). */
  sendMessage: async (
    sessionId: string,
    content: string,
    agentId?: string | null,
    onEvent?: (event: SSEEvent) => void,
  ): Promise<void> => {
    const token = localStorage.getItem('pct_token');
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const response = await fetch(`${baseUrl}/api/chat/sessions/${sessionId}/send`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content, agent_id: agentId }),
    });

    if (!response.ok || !response.body) {
      throw new Error(`SSE request failed: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const raw = JSON.parse(line.slice(6));
            // Normalize raw backend format to SSEEvent
            let event: SSEEvent;
            if ('token' in raw) {
              event = { type: 'token', content: raw.token };
            } else if ('done' in raw) {
              event = { type: 'done', message: raw.message };
            } else if ('error' in raw) {
              event = { type: 'error', content: raw.error };
            } else {
              continue;
            }
            onEvent?.(event);
          } catch {
            // Skip malformed events
          }
        }
      }
    }
  },

  updateMessage: (sessionId: string, messageId: string, data: Partial<ChatMessage>) =>
    client.put<ChatMessage>(`/api/chat/sessions/${sessionId}/messages/${messageId}`, data).then((r) => r.data),

  deleteMessage: (sessionId: string, messageId: string) =>
    client.delete(`/api/chat/sessions/${sessionId}/messages/${messageId}`),

  truncateFrom: (sessionId: string, messageId: string) =>
    client.delete(`/api/chat/sessions/${sessionId}/messages/${messageId}/truncate`),
};
