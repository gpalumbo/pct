/** Shared chat state hook — used by PlanningChat and TaskDetailPanel. */

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { message as antMessage } from 'antd';
import { useQueryClient } from '@tanstack/react-query';
import {
  useDefaultSession,
  useMessages,
  useUpdateMessage,
  useDeleteMessage,
  useTruncateFromMessage,
} from './useChatQueries';
import { useProject } from './useConfigQueries';
import { createSession, fetchSession, sendMessageStream } from '../api/chatApi';
import { boardApi } from '../api/boardApi';
import type { ChatMessage } from '../types/chat';
import type { AgentType } from '../types/enums';

export interface UsePlanningChatOptions {
  /** Explicit session ID. When omitted the global default session is used. */
  sessionId?: string;
  /** Optional artifact path forwarded to the send-message API. */
  artifactPath?: string;
  /** Feature ID for artifact append (task context only). */
  featureId?: string;
  /** Task ID for artifact append (task context only). */
  taskId?: string;
  /** Current workflow stage of the task (e.g. "draft"). */
  taskStage?: string;
  /** Called when the selected agent's type changes (or null if cleared/unknown). */
  onAgentTypeChange?: (agentType: AgentType | null) => void;
  /** When provided, imagegen-type agent prompts are routed here instead of chat API. */
  onImageGenerate?: (prompt: string) => void;
}

export interface UsePlanningChatReturn {
  activeSessionId: string | null;
  sessionLoading: boolean;
  messagesLoading: boolean;
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingContent: string;
  statusMessage: string | null;
  selectedAgent: string | null;
  handleAgentChange: (agentId: string | null) => void;
  handleSend: (content: string, agentId: string | null) => void;
  handleStop: () => void;
  handleReplay: (msg: ChatMessage) => void;
  handleTruncateAndReplay: (msg: ChatMessage) => Promise<void>;
  handleUpdateMessage: (
    id: string,
    updates: { role?: string; content?: string; included?: boolean },
  ) => void;
  handleDeleteMessage: (id: string) => void;
  handleCopyToArtifact: ((content: string) => Promise<void>) | undefined;
}

export default function usePlanningChat(options: UsePlanningChatOptions): UsePlanningChatReturn {
  const {
    sessionId: sessionIdProp,
    artifactPath,
    featureId,
    taskId,
    taskStage,
    onAgentTypeChange,
    onImageGenerate,
  } = options;

  const queryClient = useQueryClient();

  /* ------------------------------------------------------------------ */
  /*  Session resolution                                                 */
  /* ------------------------------------------------------------------ */
  const { data: defaultSession, isLoading: defaultSessionLoading } = useDefaultSession();
  const [explicitSessionReady, setExplicitSessionReady] = useState(false);
  const [explicitSessionLoading, setExplicitSessionLoading] = useState(!!sessionIdProp);

  useEffect(() => {
    if (!sessionIdProp) return;
    let cancelled = false;
    setExplicitSessionLoading(true);
    setExplicitSessionReady(false);
    (async () => {
      try {
        try {
          await fetchSession(sessionIdProp);
        } catch {
          await createSession(sessionIdProp, sessionIdProp);
        }
        if (!cancelled) setExplicitSessionReady(true);
      } catch (err) {
        console.error('Failed to init chat session:', err);
      } finally {
        if (!cancelled) setExplicitSessionLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionIdProp]);

  const activeSessionId = sessionIdProp || defaultSession?.id || null;
  const sessionLoading = sessionIdProp ? explicitSessionLoading : defaultSessionLoading;

  /* ------------------------------------------------------------------ */
  /*  Local state                                                        */
  /* ------------------------------------------------------------------ */
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const selectedAgentRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const isStreamingRef = useRef(false);

  const handleAgentChange = useCallback((agentId: string | null) => {
    setSelectedAgent(agentId);
    selectedAgentRef.current = agentId;
  }, []);

  /* ------------------------------------------------------------------ */
  /*  Initialize agent from workflow stage default & notify parent        */
  /* ------------------------------------------------------------------ */
  const { data: project } = useProject();
  const agents = useMemo(() => project?.agents ?? [], [project?.agents]);
  const stages = useMemo(() => project?.workflow_stages ?? [], [project?.workflow_stages]);

  const initializedRef = useRef(false);
  useEffect(() => {
    if (initializedRef.current || !taskStage || stages.length === 0) return;
    const stage = stages.find((s) => s.id === taskStage);
    if (stage?.agent_id) {
      handleAgentChange(stage.agent_id);
    }
    initializedRef.current = true;
  }, [taskStage, stages, handleAgentChange]);

  useEffect(() => {
    if (!onAgentTypeChange) return;
    if (!selectedAgent) {
      onAgentTypeChange(null);
      return;
    }
    const cfg = agents.find((a) => a.id === selectedAgent);
    onAgentTypeChange(cfg?.agent_type ?? null);
  }, [selectedAgent, agents, onAgentTypeChange]);

  /* ------------------------------------------------------------------ */
  /*  Load messages                                                      */
  /* ------------------------------------------------------------------ */
  const enabledSessionId = sessionIdProp
    ? explicitSessionReady
      ? activeSessionId
      : null
    : activeSessionId;

  const { data: fetchedMessages, isLoading: messagesLoading } = useMessages(enabledSessionId);

  useEffect(() => {
    if (fetchedMessages && !isStreamingRef.current) {
      setMessages(fetchedMessages);
    }
  }, [fetchedMessages]);

  /* ------------------------------------------------------------------ */
  /*  Mutations                                                          */
  /* ------------------------------------------------------------------ */
  const updateMutation = useUpdateMessage(activeSessionId);
  const deleteMutation = useDeleteMessage(activeSessionId);
  const truncateMutation = useTruncateFromMessage(activeSessionId);

  const handleUpdateMessage = useCallback(
    (id: string, updates: { role?: string; content?: string; included?: boolean }) => {
      if (!activeSessionId) return;
      updateMutation.mutate(
        { messageId: id, data: updates },
        {
          onSuccess: (updated) => {
            setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...updated } : m)));
          },
        },
      );
    },
    [activeSessionId, updateMutation],
  );

  const handleDeleteMessage = useCallback(
    (id: string) => {
      if (!activeSessionId) return;
      setMessages((prev) => prev.filter((m) => m.id !== id));
      deleteMutation.mutate(id);
    },
    [activeSessionId, deleteMutation],
  );

  /* ------------------------------------------------------------------ */
  /*  Send / replay / truncate-and-replay                                */
  /* ------------------------------------------------------------------ */
  const handleSend = useCallback(
    (content: string, agentId: string | null) => {
      if (!activeSessionId) return;

      // Route imagegen prompts to image generation instead of chat
      const agentCfg = agentId ? agents.find((a) => a.id === agentId) : null;
      if (agentCfg?.agent_type === 'image_gen' && onImageGenerate) {
        onImageGenerate(content);
        return;
      }

      const userMsg: ChatMessage = {
        id: crypto.randomUUID().slice(0, 12),
        role: 'user',
        content,
        created_at: new Date().toISOString(),
        tokens: null,
        included: true,
        agent_id: null,
        model_id: null,
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);
      isStreamingRef.current = true;
      setStreamingContent('');
      setStatusMessage(null);

      const onDone = (message: ChatMessage) => {
        setMessages((prev) => [...prev, message]);
        setIsStreaming(false);
        isStreamingRef.current = false;
        setStreamingContent('');
        setStatusMessage(null);
        abortRef.current = null;
        queryClient.invalidateQueries({ queryKey: ['chat-messages', activeSessionId] });
      };

      const controller = sendMessageStream(
        activeSessionId,
        content,
        agentId,
        (token) => setStreamingContent((prev) => prev + token),
        onDone,
        (error) => {
          console.error('Chat stream error:', error);
          onDone({
            id: crypto.randomUUID().slice(0, 12),
            role: 'assistant',
            content: `Error: ${error}`,
            created_at: new Date().toISOString(),
            tokens: null,
            included: true,
            agent_id: null,
            model_id: null,
          });
        },
        artifactPath,
        (status) => setStatusMessage(status),
      );
      abortRef.current = controller;
    },
    [activeSessionId, artifactPath, queryClient, agents, onImageGenerate],
  );

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
    isStreamingRef.current = false;
    setStreamingContent('');
    setStatusMessage(null);
    abortRef.current = null;
  }, []);

  const handleReplay = useCallback(
    (msg: ChatMessage) => {
      handleSend(msg.content, selectedAgentRef.current);
    },
    [handleSend],
  );

  const handleTruncateAndReplay = useCallback(
    async (msg: ChatMessage) => {
      if (!activeSessionId) return;
      const content = msg.content;
      setMessages((prev) => {
        const idx = prev.findIndex((m) => m.id === msg.id);
        return idx === -1 ? prev : prev.slice(0, idx);
      });
      await truncateMutation.mutateAsync(msg.id);
      handleSend(content, selectedAgentRef.current);
    },
    [activeSessionId, truncateMutation, handleSend],
  );

  /* ------------------------------------------------------------------ */
  /*  Copy to artifact (append)                                          */
  /* ------------------------------------------------------------------ */
  const handleCopyToArtifact = useCallback(
    async (content: string) => {
      if (!featureId || !taskId) return;
      try {
        const artifact = await boardApi.getArtifact(featureId, taskId);
        const updated = artifact.content ? artifact.content + '\n\n' + content : content;
        await boardApi.putArtifact(featureId, taskId, updated);
        queryClient.invalidateQueries({ queryKey: ['artifact', featureId, taskId] });
        antMessage.success('Appended to artifact');
      } catch {
        antMessage.error('Failed to append to artifact');
      }
    },
    [featureId, taskId, queryClient],
  );

  return {
    activeSessionId,
    sessionLoading,
    messagesLoading,
    messages,
    isStreaming,
    streamingContent,
    statusMessage,
    selectedAgent,
    handleAgentChange,
    handleSend,
    handleStop,
    handleReplay,
    handleTruncateAndReplay,
    handleUpdateMessage,
    handleDeleteMessage,
    handleCopyToArtifact: featureId && taskId ? handleCopyToArtifact : undefined,
  };
}
