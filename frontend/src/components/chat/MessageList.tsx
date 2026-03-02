import { useRef, useEffect } from 'react';
import { Empty } from 'antd';
import MessageBubble from './MessageBubble';
import type { ChatMessage } from '../../types/chat';

interface MessageListProps {
  sessionId: string;
  messages: ChatMessage[];
  streamContent?: string;
  onToggleInclude: (messageId: string, included: boolean) => void;
  onEdit?: (messageId: string) => void;
  onDelete: (messageId: string) => void;
}

export default function MessageList({ messages, sessionId, streamContent, onToggleInclude, onEdit, onDelete }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, streamContent]);

  if (messages.length === 0 && !streamContent) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Empty description="No messages yet" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </div>
    );
  }

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '8px 4px' }}>
      {messages.map((msg, idx) => (
        <MessageBubble
          key={msg.id}
          message={msg}
          messageIndex={idx}
          sessionId={sessionId}
          onToggleInclude={onToggleInclude}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}

      {streamContent && (
        <div
          style={{
            maxWidth: '80%',
            padding: '8px 12px',
            borderRadius: 8,
            backgroundColor: '#f6ffed',
            border: '1px solid #b7eb8f',
            fontSize: 13,
            opacity: 0.8,
          }}
        >
          {streamContent}
          <span className="streaming-cursor" style={{ animation: 'blink 1s infinite' }}>
            |
          </span>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
