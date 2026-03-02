/** Chat types — mirrors backend models. */

import type { MessageRole } from './enums';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  included: boolean;
  created_at: string;
}

export interface SendMessage {
  content: string;
  agent_id?: string | null;
}

export interface SSEEvent {
  type: 'token' | 'done' | 'error';
  content?: string;
  message_id?: string;
}
