import { useEffect, useRef } from 'react';
import { Spin, Tag } from 'antd';
import ReactMarkdown from 'react-markdown';
import MessageBubble from './MessageBubble';
import type { PlanningMessage } from '../../types/chat';

interface Props {
  messages: PlanningMessage[];
  streamingContent: string;
  isStreaming: boolean;
  onUpdateMessage?: (id: string, updates: { role?: string; content?: string; included?: boolean }) => void;
  onDeleteMessage?: (id: string) => void;
  onReplay?: (msg: PlanningMessage) => void;
  onTruncateAndReplay?: (msg: PlanningMessage) => void;
  onCopyToArtifact?: (content: string) => void;
}

export default function MessageList({ messages, streamingContent, isStreaming, onUpdateMessage, onDeleteMessage, onReplay, onTruncateAndReplay, onCopyToArtifact }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, streamingContent]);

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '16px 16px 0' }}>
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} onUpdate={onUpdateMessage} onDelete={onDeleteMessage} onReplay={onReplay} onTruncateAndReplay={onTruncateAndReplay} onCopyToArtifact={onCopyToArtifact} isStreaming={isStreaming} />
      ))}

      {/* Streaming indicator: temporary assistant bubble */}
      {isStreaming && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', marginBottom: 12 }}>
          <Tag color="green" style={{ marginBottom: 2 }}>assistant</Tag>
          <div style={{ background: '#f6ffed', borderRadius: 8, padding: '8px 12px', maxWidth: '80%' }}>
            {streamingContent ? (
              <ReactMarkdown>{streamingContent}</ReactMarkdown>
            ) : (
              <Spin size="small" />
            )}
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
