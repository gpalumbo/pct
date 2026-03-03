/** Chat types — mirrors backend chat.models. */

export interface ChatMessage {
  id: string;
  role: string;
  content: string;
  created_at: string;
  tokens: number | null;
  included: boolean;
  agent_id: string | null;
  model_id: string | null;
}

export interface ChatSession {
  id: string;
  title: string;
  agent_id: string | null;
  created: string;
  updated: string;
  message_count: number;
}

export interface SendMessageRequest {
  content: string;
  agent_id?: string | null;
  artifact_path?: string | null;
}

export interface UpdateMessageRequest {
  role?: string;
  content?: string;
  included?: boolean;
}

// SSE event types
export type SSEEvent =
  | { type: 'token'; content: string; message?: undefined }
  | { type: 'done'; content?: undefined; message: ChatMessage }
  | { type: 'error'; content: string; message?: undefined };
