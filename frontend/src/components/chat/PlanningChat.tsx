import { Spin, Typography } from 'antd';
import usePlanningChat from '../../hooks/usePlanningChat';
import type { AgentType } from '../../types/config';
import MessageList from './MessageList';
import ChatInput from './ChatInput';

const { Text } = Typography;

interface PlanningChatProps {
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

export default function PlanningChat({
  sessionId,
  artifactPath,
  featureId,
  taskId,
  taskStage,
  onAgentTypeChange,
  onImageGenerate,
}: PlanningChatProps) {
  const chat = usePlanningChat({
    sessionId,
    artifactPath,
    featureId,
    taskId,
    taskStage,
    onAgentTypeChange,
    onImageGenerate,
  });

  if (chat.sessionLoading || chat.messagesLoading) {
    return (
      <div
        style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}
      >
        <Spin tip="Loading chat...">
          <div />
        </Spin>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {chat.activeSessionId && (
        <div style={{ padding: '4px 16px', borderBottom: '1px solid #f0f0f0' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Session: {chat.activeSessionId}
          </Text>
        </div>
      )}
      <MessageList
        messages={chat.messages}
        streamingContent={chat.streamingContent}
        isStreaming={chat.isStreaming}
        onUpdateMessage={chat.handleUpdateMessage}
        onDeleteMessage={chat.handleDeleteMessage}
        onReplay={chat.handleReplay}
        onTruncateAndReplay={chat.handleTruncateAndReplay}
        onCopyToArtifact={chat.handleCopyToArtifact}
      />
      <ChatInput
        isStreaming={chat.isStreaming}
        onSend={chat.handleSend}
        onStop={chat.handleStop}
        selectedAgent={chat.selectedAgent}
        onAgentChange={chat.handleAgentChange}
        taskStage={taskStage}
      />
    </div>
  );
}
