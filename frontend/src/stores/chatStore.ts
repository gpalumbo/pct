import { create } from 'zustand';
import type { PlanningMessage } from '../types/chat';

interface ChatState {
  activeSessionId: string | null;
  messages: PlanningMessage[];
  isStreaming: boolean;
  streamingContent: string;
  abortController: AbortController | null;

  setActiveSession: (id: string) => void;
  setMessages: (messages: PlanningMessage[]) => void;
  addMessage: (message: PlanningMessage) => void;
  updateMessage: (id: string, updates: Partial<PlanningMessage>) => void;
  startStreaming: (controller: AbortController) => void;
  appendToken: (token: string) => void;
  finishStreaming: (message: PlanningMessage) => void;
  cancelStreaming: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  activeSessionId: null,
  messages: [],
  isStreaming: false,
  streamingContent: '',
  abortController: null,

  setActiveSession: (id) => set({ activeSessionId: id }),

  setMessages: (messages) => set({ messages }),

  addMessage: (message) => set((s) => ({ messages: [...s.messages, message] })),

  updateMessage: (id, updates) =>
    set((s) => ({
      messages: s.messages.map((m) => (m.id === id ? { ...m, ...updates } : m)),
    })),

  startStreaming: (controller) =>
    set({ isStreaming: true, streamingContent: '', abortController: controller }),

  appendToken: (token) =>
    set((s) => ({ streamingContent: s.streamingContent + token })),

  finishStreaming: (message) =>
    set((s) => ({
      isStreaming: false,
      streamingContent: '',
      abortController: null,
      messages: [...s.messages, message],
    })),

  cancelStreaming: () => {
    const { abortController } = get();
    if (abortController) abortController.abort();
    set({ isStreaming: false, streamingContent: '', abortController: null });
  },
}));
