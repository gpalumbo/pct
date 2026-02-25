import { useEffect, useRef, useState, useCallback } from 'react';
import { Spin, Typography } from 'antd';
import { useQueryClient } from '@tanstack/react-query';
import { useDefaultSession, useMessages, useUpdateMessage, useDeleteMessage, useTruncateFromMessage } from '../../hooks/useChatQueries';
import { createSession, fetchSession, sendMessageStream } from '../../api/chatApi';
import type { PlanningMessage } from '../../types/chat';
import MessageList from './MessageList';
import ChatInput from './ChatInput';

const { Text } = Typography;

interface PlanningChatProps {
  /** Explicit session ID. When omitted the global default session is used. */
  sessionId?: string;
  /** Optional artifact path forwarded to the send-message API. */
  artifactPath?: string;
}

export default function PlanningChat({ sessionId: sessionIdProp, artifactPath }: PlanningChatProps) {
  const queryClient = useQueryClient();

  /* ------------------------------------------------------------------ */
  /*  Session resolution                                                 */
  /* ------------------------------------------------------------------ */
  const { data: defaultSession, isLoading: defaultSessionLoading } = useDefaultSession();
  const [explicitSessionReady, setExplicitSessionReady] = useState(false);
  const [explicitSessionLoading, setExplicitSessionLoading] = useState(!!sessionIdProp);

  // When an explicit sessionId is provided, ensure it exists on the server.
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
    return () => { cancelled = true; };
  }, [sessionIdProp]);

  const activeSessionId = sessionIdProp || defaultSession?.id || null;
  const sessionLoading = sessionIdProp ? explicitSessionLoading : defaultSessionLoading;

  /* ------------------------------------------------------------------ */
  /*  Local state (each instance is independent)                         */
  /* ------------------------------------------------------------------ */
  const [messages, setMessages] = useState<PlanningMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const selectedAgentRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const isStreamingRef = useRef(false);

  const handleAgentChange = useCallback((agentId: string | null) => {
    setSelectedAgent(agentId);
    selectedAgentRef.current = agentId;
  }, []);

  /* ------------------------------------------------------------------ */
  /*  Load messages                                                      */
  /* ------------------------------------------------------------------ */
  const enabledSessionId = sessionIdProp
    ? (explicitSessionReady ? activeSessionId : null)
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

      const userMsg: PlanningMessage = {
        id: crypto.randomUUID().slice(0, 12),
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
        tokens: null,
        included: true,
        agent_id: null,
        model_id: null,
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);
      isStreamingRef.current = true;
      setStreamingContent('');

      const onDone = (message: PlanningMessage) => {
        setMessages((prev) => [...prev, message]);
        setIsStreaming(false);
        isStreamingRef.current = false;
        setStreamingContent('');
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
            timestamp: new Date().toISOString(),
            tokens: null,
            included: true,
            agent_id: null,
            model_id: null,
          });
        },
        artifactPath,
      );
      abortRef.current = controller;
    },
    [activeSessionId, artifactPath, queryClient],
  );

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
    isStreamingRef.current = false;
    setStreamingContent('');
    abortRef.current = null;
  }, []);

  const handleReplay = useCallback(
    (msg: PlanningMessage) => {
      handleSend(msg.content, selectedAgentRef.current);
    },
    [handleSend],
  );

  const handleTruncateAndReplay = useCallback(
    async (msg: PlanningMessage) => {
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
  /*  Render                                                             */
  /* ------------------------------------------------------------------ */
  if (sessionLoading || messagesLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <Spin tip="Loading chat..."><div /></Spin>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {activeSessionId && (
        <div style={{ padding: '4px 16px', borderBottom: '1px solid #f0f0f0' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Session: {activeSessionId}
          </Text>
        </div>
      )}
      <MessageList
        messages={messages}
        streamingContent={streamingContent}
        isStreaming={isStreaming}
        onUpdateMessage={handleUpdateMessage}
        onDeleteMessage={handleDeleteMessage}
        onReplay={handleReplay}
        onTruncateAndReplay={handleTruncateAndReplay}
      />
      <ChatInput
        isStreaming={isStreaming}
        onSend={handleSend}
        onStop={handleStop}
        selectedAgent={selectedAgent}
        onAgentChange={handleAgentChange}
      />
    </div>
  );
}
