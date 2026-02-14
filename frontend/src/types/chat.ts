export interface PlanningMessage {
  id: string;
  role: string;
  content: string;
  timestamp: string;
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
}

export interface UpdateMessageRequest {
  role?: string;
  content?: string;
  included?: boolean;
}

// SSE event types
export interface TokenEvent {
  token: string;
}

export interface DoneEvent {
  done: true;
  message: PlanningMessage;
}

export interface ErrorEvent {
  error: string;
}

export type SSEEvent = TokenEvent | DoneEvent | ErrorEvent;
