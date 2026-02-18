import { useEffect, useRef, useState, useCallback } from 'react';
import { Spin, Typography } from 'antd';
import { useQueryClient } from '@tanstack/react-query';
import { createSession, fetchSession, fetchMessages, sendMessageStream } from '../../api/chatApi';
import type { PlanningMessage } from '../../types/chat';
import MessageList from '../chat/MessageList';
import ChatInput from '../chat/ChatInput';

const { Text } = Typography;

interface TaskChatProps {
  sessionId: string;
  artifactPath?: string;
}

export default function TaskChat({ sessionId, artifactPath }: TaskChatProps) {
  const queryClient = useQueryClient();

  const [messages, setMessages] = useState<PlanningMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [loading, setLoading] = useState(true);
  const abortRef = useRef<AbortController | null>(null);
  const isStreamingRef = useRef(false);

  // Ensure session exists and load messages
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        // Try fetching existing session; create if not found
        try {
          await fetchSession(sessionId);
        } catch {
          await createSession(sessionId, sessionId);
        }
        const msgs = await fetchMessages(sessionId);
        if (!cancelled) setMessages(msgs);
      } catch (err) {
        console.error('Failed to init task chat session:', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [sessionId]);

  const handleSend = useCallback((content: string, agentId: string | null) => {
    // Optimistic user message
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

    const onToken = (token: string) => {
      setStreamingContent((prev) => prev + token);
    };

    const onDone = (message: PlanningMessage) => {
      setMessages((prev) => [...prev, message]);
      setIsStreaming(false);
      isStreamingRef.current = false;
      setStreamingContent('');
      abortRef.current = null;
      queryClient.invalidateQueries({ queryKey: ['chat-messages', sessionId] });
    };

    const onError = (error: string) => {
      console.error('Task chat stream error:', error);
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
    };

    const controller = sendMessageStream(
      sessionId, content, agentId, onToken, onDone, onError, artifactPath,
    );
    abortRef.current = controller;
  }, [sessionId, artifactPath, queryClient]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
    isStreamingRef.current = false;
    setStreamingContent('');
    abortRef.current = null;
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <Spin size="small" />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '4px 12px', borderBottom: '1px solid #f0f0f0' }}>
        <Text style={{ fontSize: 11, color: '#333' }}>
          Session: {sessionId}
        </Text>
      </div>
      <MessageList
        messages={messages}
        streamingContent={streamingContent}
        isStreaming={isStreaming}
      />
      <ChatInput isStreaming={isStreaming} onSend={handleSend} onStop={handleStop} />
    </div>
  );
}
