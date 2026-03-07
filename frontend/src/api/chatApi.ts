/** Chat API wrapper with SSE streaming support. */

import client from './client';
import { connectSSE } from './sseStream';
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
export interface SendMessageStreamOptions {
  sessionId: string;
  content: string;
  agentId?: string | null;
  artifactPath?: string;
  featureId?: string | null;
  taskId?: string | null;
  onToken: (token: string) => void;
  onDone: (message: ChatMessage) => void;
  onError: (error: string) => void;
  onStatus?: (status: string) => void;
  onToolCall?: (call: { id: string; name: string; arguments: string }) => void;
  onToolResult?: (result: { id: string; name: string; output: string }) => void;
  onSystemPrompt?: (prompt: string) => void;
  onFlushBubble?: (content: string) => void;
}

export function sendMessageStream(
  sessionId: string,
  content: string,
  agentId: string | null | undefined,
  onToken: (token: string) => void,
  onDone: (message: ChatMessage) => void,
  onError: (error: string) => void,
  artifactPath?: string,
  onStatus?: (status: string) => void,
  onToolCall?: (call: { id: string; name: string; arguments: string }) => void,
  onToolResult?: (result: { id: string; name: string; output: string }) => void,
  onSystemPrompt?: (prompt: string) => void,
  featureId?: string | null,
  taskId?: string | null,
  onFlushBubble?: (content: string) => void,
): AbortController {
  const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const body: Record<string, unknown> = { content };
  if (agentId) body.agent_id = agentId;
  if (artifactPath) body.artifact_path = artifactPath;
  if (featureId) body.feature_id = featureId;
  if (taskId) body.task_id = taskId;

  return connectSSE({
    url: `${baseURL}/api/chat/sessions/${sessionId}/send`,
    method: 'POST',
    body,
    onEvent: (event) => {
      if ('token' in event) onToken(event.token as string);
      else if ('done' in event) onDone(event.message as ChatMessage);
      else if ('error' in event) onError(event.error as string);
      else if ('status' in event) onStatus?.(event.status as string);
      else if ('tool_call' in event) onToolCall?.(event.tool_call as { id: string; name: string; arguments: string });
      else if ('tool_result' in event) onToolResult?.(event.tool_result as { id: string; name: string; output: string });
      else if ('system_prompt' in event) onSystemPrompt?.(event.system_prompt as string);
      else if ('flush_bubble' in event) onFlushBubble?.(event.flush_bubble as string);
    },
    onError,
  });
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
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    return new Promise<void>((resolve, reject) => {
      connectSSE({
        url: `${baseUrl}/api/chat/sessions/${sessionId}/send`,
        method: 'POST',
        body: { content, agent_id: agentId },
        signal,
        onEvent: (raw) => {
          let event: SSEEvent;
          if ('token' in raw) event = { type: 'token', content: raw.token as string };
          else if ('done' in raw) { event = { type: 'done', message: raw.message as ChatMessage }; onEvent?.(event); resolve(); return; }
          else if ('error' in raw) { event = { type: 'error', content: raw.error as string }; onEvent?.(event); reject(new Error(raw.error as string)); return; }
          else if ('status' in raw) event = { type: 'status', content: raw.status as string };
          else if ('tool_call' in raw) event = { type: 'tool_call', toolCall: raw.tool_call as { id: string; name: string; arguments: string } };
          else if ('tool_result' in raw) event = { type: 'tool_result', toolResult: raw.tool_result as { id: string; name: string; output: string } };
          else if ('system_prompt' in raw) event = { type: 'system_prompt', content: raw.system_prompt as string };
          else if ('flush_bubble' in raw) event = { type: 'flush_bubble', content: raw.flush_bubble as string };
          else return;
          onEvent?.(event);
        },
        onError: (err) => reject(new Error(err)),
      });
    });
  },
  updateMessage,
  deleteMessage,
  truncateFrom: truncateFromMessage,
};
