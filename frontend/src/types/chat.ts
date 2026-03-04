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
  tool_call_id?: string | null;
  tool_name?: string | null;
}

export interface ChatSession {
  id: string;
  title: string;
  agent_id: string | null;
  feature_id: string | null;
  task_id: string | null;
  stage_id: string | null;
  created: string;
  updated: string;
  message_count: number;
}

export interface SendMessageRequest {
  content: string;
  agent_id?: string | null;
  artifact_path?: string | null;
  feature_id?: string | null;
  task_id?: string | null;
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
  | { type: 'error'; content: string; message?: undefined }
  | { type: 'status'; content: string; message?: undefined }
  | { type: 'tool_call'; content?: undefined; toolCall: { id: string; name: string; arguments: string } }
  | { type: 'tool_result'; content?: undefined; toolResult: { id: string; name: string; output: string } }
  | { type: 'system_prompt'; content: string; message?: undefined }
  | { type: 'flush_bubble'; content: string; message?: undefined };
