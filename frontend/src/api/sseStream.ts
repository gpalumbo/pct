/** Shared SSE stream reader — generic fetch + ReadableStream + line-buffer + JSON parse. */

import { useAuthStore } from '../stores/authStore';

export interface SSEStreamOptions {
  url: string;
  method?: 'GET' | 'POST';
  body?: Record<string, unknown>;
  onEvent: (event: Record<string, unknown>) => void;
  onError?: (error: string) => void;
  signal?: AbortSignal;
}

/**
 * Open an SSE connection via fetch + ReadableStream.
 * Returns an AbortController to cancel the stream.
 */
export function connectSSE(options: SSEStreamOptions): AbortController {
  const { url, method = 'GET', body, onEvent, onError, signal: externalSignal } = options;
  const controller = new AbortController();
  const token = useAuthStore.getState().token;

  // Combine external signal with our controller
  const signal = externalSignal ?? controller.signal;

  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (body) headers['Content-Type'] = 'application/json';

  fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        onError?.(`HTTP ${response.status}: ${response.statusText}`);
        return;
      }
      const reader = response.body?.getReader();
      if (!reader) {
        onError?.('No response body');
        return;
      }
      const decoder = new TextDecoder();
      let buffer = '';

      let done = false;
      while (!done) {
        const result = await reader.read();
        if (result.done) {
          done = true;
          break;
        }

        buffer += decoder.decode(result.value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const event = JSON.parse(line.slice(6));
            onEvent(event);
          } catch {
            // skip malformed lines
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError?.(err.message || 'Stream failed');
      }
    });

  return controller;
}
