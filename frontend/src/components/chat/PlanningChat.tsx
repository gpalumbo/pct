import { useEffect, useRef } from 'react';
import { Spin, Typography } from 'antd';
import { useQueryClient } from '@tanstack/react-query';
import { useChatStore } from '../../stores/chatStore';
import { useDefaultSession, useMessages, useUpdateMessage, useDeleteMessage } from '../../hooks/useChatQueries';
import { sendMessageStream } from '../../api/chatApi';
import type { PlanningMessage } from '../../types/chat';
import MessageList from './MessageList';
import ChatInput from './ChatInput';

const { Text } = Typography;

export default function PlanningChat() {
  const {
    activeSessionId,
    messages,
    isStreaming,
    streamingContent,
    setActiveSession,
    setMessages,
    addMessage,
    updateMessage: updateStoreMessage,
    removeMessage: removeStoreMessage,
    startStreaming,
    appendToken,
    finishStreaming,
    cancelStreaming,
  } = useChatStore();

  const queryClient = useQueryClient();
  const isStreamingRef = useRef(isStreaming);
  isStreamingRef.current = isStreaming;

  // 1. Init: get or create default session
  const { data: session, isLoading: sessionLoading } = useDefaultSession();

  useEffect(() => {
    if (session?.id && session.id !== activeSessionId) {
      setActiveSession(session.id);
    }
  }, [session?.id, activeSessionId, setActiveSession]);

  // 2. Load messages when session is set
  const { data: fetchedMessages, isLoading: messagesLoading } = useMessages(activeSessionId);

  useEffect(() => {
    if (fetchedMessages && !isStreamingRef.current) {
      setMessages(fetchedMessages);
    }
  }, [fetchedMessages, setMessages]);

  // 3. Message update/delete mutations
  const updateMutation = useUpdateMessage(activeSessionId);
  const deleteMutation = useDeleteMessage(activeSessionId);

  const handleUpdateMessage = (id: string, updates: { role?: string; content?: string; included?: boolean }) => {
    if (!activeSessionId) return;
    updateMutation.mutate(
      { messageId: id, data: updates },
      {
        onSuccess: (updated) => updateStoreMessage(id, updated),
      },
    );
  };

  const handleDeleteMessage = (id: string) => {
    if (!activeSessionId) return;
    removeStoreMessage(id);
    deleteMutation.mutate(id);
  };

  // 4. Send message with streaming
  const handleSend = (content: string, agentId: string | null) => {
    if (!activeSessionId) return;

    // Optimistically add user message
    const userMsg = {
      id: crypto.randomUUID().slice(0, 12),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
      tokens: null,
      included: true,
      agent_id: null,
      model_id: null,
    };
    addMessage(userMsg);

    const onDone = (message: PlanningMessage) => {
      finishStreaming(message);
      queryClient.invalidateQueries({ queryKey: ['chat-messages', activeSessionId] });
    };

    const controller = sendMessageStream(
      activeSessionId,
      content,
      agentId,
      (token) => appendToken(token),
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
    );
    startStreaming(controller);
  };

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
      />
      <ChatInput isStreaming={isStreaming} onSend={handleSend} onStop={cancelStreaming} />
    </div>
  );
}
