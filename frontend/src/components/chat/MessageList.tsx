import { useEffect, useRef, useState } from 'react';
import { Collapse, Spin, Switch, Tag, Typography } from 'antd';
import { LoadingOutlined, ToolOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import MessageBubble from './MessageBubble';
import type { ChatMessage } from '../../types/chat';
import type { ToolActivity } from '../../hooks/usePlanningChat';

const { Text } = Typography;

interface Props {
  sessionId: string;
  messages: ChatMessage[];
  streamingContent: string;
  isStreaming: boolean;
  statusMessage?: string | null;
  systemPrompt?: string | null;
  toolActivity?: ToolActivity[];
  onUpdateMessage?: (
    id: string,
    updates: { role?: string; content?: string; included?: boolean },
  ) => void;
  onDeleteMessage?: (id: string) => void;
  onReplay?: (msg: ChatMessage) => void;
  onTruncate?: (msg: ChatMessage) => void;
  onCopyToArtifact?: (content: string) => void;
}

export default function MessageList({
  sessionId,
  messages,
  streamingContent,
  isStreaming,
  statusMessage,
  systemPrompt,
  toolActivity = [],
  onUpdateMessage,
  onDeleteMessage,
  onReplay,
  onTruncate,
  onCopyToArtifact,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [showToolCalls, setShowToolCalls] = useState(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, streamingContent, toolActivity.length]);

  // Always filter system and tool_call roles — system prompt shown in collapse,
  // tool_calls are transient (synthesized from tool_results for the LLM).
  const filteredMessages = messages
    .filter((m) => m.role !== 'system' && m.role !== 'tool_call')
    .filter((m) => showToolCalls || m.role !== 'tool_result');

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '16px 16px 0' }}>
      {/* Controls bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
        <Switch
          size="small"
          checked={showToolCalls}
          onChange={setShowToolCalls}
          checkedChildren={<ToolOutlined />}
        />
        <Text type="secondary" style={{ fontSize: 12 }}>
          Show tool calls
        </Text>
      </div>

      {/* System prompt collapse */}
      {systemPrompt && (
        <Collapse
          size="small"
          style={{ marginBottom: 12 }}
          items={[
            {
              key: 'system',
              label: (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  System prompt
                </Text>
              ),
              children: (
                <pre
                  style={{
                    fontSize: 11,
                    maxHeight: 200,
                    overflow: 'auto',
                    whiteSpace: 'pre-wrap',
                    margin: 0,
                  }}
                >
                  {systemPrompt}
                </pre>
              ),
            },
          ]}
        />
      )}

      {filteredMessages.map((msg, idx) => (
        <MessageBubble
          key={msg.id}
          message={msg}
          messageIndex={idx}
          sessionId={sessionId}
          onUpdate={onUpdateMessage}
          onDelete={onDeleteMessage}
          onReplay={onReplay}
          onTruncate={onTruncate}
          onCopyToArtifact={onCopyToArtifact}
          isStreaming={isStreaming}
        />
      ))}

      {/* Streaming indicator: temporary assistant bubble */}
      {isStreaming && (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'flex-start',
            marginBottom: 12,
          }}
        >
          <Tag color="green" style={{ marginBottom: 2 }}>
            assistant
          </Tag>
          {statusMessage && (
            <Tag color="blue" style={{ marginBottom: 4 }}>
              {statusMessage}
            </Tag>
          )}

          {/* Live tool activity */}
          {toolActivity.length > 0 && (
            <div style={{ marginBottom: 8, width: '80%' }}>
              {toolActivity.map((ta) => (
                <div
                  key={ta.callId}
                  style={{
                    background: '#f9f0ff',
                    borderRadius: 6,
                    padding: '4px 8px',
                    marginBottom: 4,
                    fontSize: 12,
                  }}
                >
                  <Tag color="purple" style={{ marginRight: 4 }}>
                    {ta.name}
                  </Tag>
                  {ta.output === undefined ? (
                    <LoadingOutlined style={{ fontSize: 11 }} />
                  ) : (
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      done
                    </Text>
                  )}
                </div>
              ))}
            </div>
          )}

          <div
            style={{ background: '#f6ffed', borderRadius: 8, padding: '8px 12px', maxWidth: '80%' }}
          >
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
