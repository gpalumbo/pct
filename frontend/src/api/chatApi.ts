/** Chat API wrapper with SSE streaming support. */

import client from './client';
import { useAuthStore } from '../stores/authStore';
import type { ChatMessage, ChatSession, UpdateMessageRequest, SSEEvent } from '../types/chat';

// Session CRUD
export const fetchSessions = () =>
  client.get<ChatSession[]>('/api/chat/sessions').then((r) => r.data);

export const createSession = (title: string = 'Planning', sessionId?: string) =>
  client
    .post<ChatSession>('/api/chat/sessions', { title, session_id: sessionId ?? null })
    .then((r) => r.data);

export const fetchSession = (sessionId: string) =>
  client.get<ChatSession>(`/api/chat/sessions/${sessionId}`).then((r) => r.data);

export const fetchDefaultSession = () =>
  client.get<ChatSession>('/api/chat/sessions/default').then((r) => r.data);

// Messages
export const fetchMessages = (sessionId: string) =>
  client.get<ChatMessage[]>(`/api/chat/sessions/${sessionId}/messages`).then((r) => r.data);

export const updateMessage = (sessionId: string, messageId: string, data: UpdateMessageRequest) =>
  client
    .put<ChatMessage>(`/api/chat/sessions/${sessionId}/messages/${messageId}`, data)
    .then((r) => r.data);

export const deleteMessage = (sessionId: string, messageId: string) =>
  client.delete(`/api/chat/sessions/${sessionId}/messages/${messageId}`);

export const truncateFromMessage = (sessionId: string, messageId: string) =>
  client.delete(`/api/chat/sessions/${sessionId}/messages/${messageId}/truncate`);

// SSE streaming (uses native fetch — Axios doesn't support ReadableStream)
export function sendMessageStream(
  sessionId: string,
  content: string,
  agentId: string | null | undefined,
  onToken: (token: string) => void,
  onDone: (message: ChatMessage) => void,
  onError: (error: string) => void,
  artifactPath?: string,
  onStatus?: (status: string) => void,
): AbortController {
  const controller = new AbortController();
  const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const token = useAuthStore.getState().token;

  const body: Record<string, unknown> = { content };
  if (agentId) body.agent_id = agentId;
  if (artifactPath) body.artifact_path = artifactPath;

  fetch(`${baseURL}/api/chat/sessions/${sessionId}/send`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        onError(`HTTP ${response.status}: ${response.statusText}`);
        return;
      }
      const reader = response.body?.getReader();
      if (!reader) {
        onError('No response body');
        return;
      }
      const decoder = new TextDecoder();
      let buffer = '';

      let done = false;
      while (!done) {
        const result = await reader.read();
        if (result.done) { done = true; break; }
        const { value } = result;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if ('token' in event) {
              onToken(event.token);
            } else if ('done' in event) {
              onDone(event.message);
            } else if ('error' in event) {
              onError(event.error);
            } else if ('status' in event) {
              onStatus?.(event.status);
            }
          } catch {
            // skip malformed lines
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError(err.message || 'Stream failed');
      }
    });

  return controller;
}

// Legacy namespace export for backwards compatibility (PlanningPage, etc.)
export const chatApi = {
  listSessions: fetchSessions,
  getDefaultSession: fetchDefaultSession,
  getMessages: fetchMessages,
  sendMessage: async (
    sessionId: string,
    content: string,
    agentId?: string | null,
    onEvent?: (event: SSEEvent) => void,
    signal?: AbortSignal,
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
      signal,
    });

    if (!response.ok || !response.body) {
      throw new Error(`SSE request failed: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let streamDone = false;

    while (!streamDone) {
      const result = await reader.read();
      if (result.done) { streamDone = true; break; }
      buffer += decoder.decode(result.value, { stream: true });

      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const raw = JSON.parse(line.slice(6));
            let event: SSEEvent;
            if ('token' in raw) {
              event = { type: 'token', content: raw.token };
            } else if ('done' in raw) {
              event = { type: 'done', message: raw.message };
            } else if ('error' in raw) {
              event = { type: 'error', content: raw.error };
            } else if ('status' in raw) {
              event = { type: 'status', content: raw.status };
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
  updateMessage,
  deleteMessage,
  truncateFrom: truncateFromMessage,
};
