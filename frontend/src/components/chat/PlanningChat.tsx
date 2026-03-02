import { useEffect } from 'react';
import { Typography, Divider } from 'antd';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import { usePlanningChat } from '../../hooks/usePlanningChat';

const { Title } = Typography;

interface PlanningChatProps {
  sessionId: string;
}

export default function PlanningChat({ sessionId }: PlanningChatProps) {
  const {
    messages,
    isStreaming,
    streamContent,
    selectedAgentId,
    setSelectedAgentId,
    sendMessage,
    refreshMessages,
    toggleIncluded,
    deleteMessage,
  } = usePlanningChat({ sessionId });

  useEffect(() => {
    refreshMessages();
  }, [refreshMessages]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      <Title level={5} style={{ margin: '0 0 4px 0', flexShrink: 0 }}>
        Chat
      </Title>

      <MessageList
        sessionId={sessionId}
        messages={messages}
        streamContent={isStreaming ? streamContent : undefined}
        onToggleInclude={toggleIncluded}
        onDelete={deleteMessage}
      />

      <Divider style={{ margin: '4px 0' }} />

      <ChatInput
        onSend={sendMessage}
        isStreaming={isStreaming}
        selectedAgentId={selectedAgentId}
        onAgentChange={setSelectedAgentId}
      />
    </div>
  );
}
