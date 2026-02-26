import { useState } from 'react';
import { Checkbox, Input, Select, Space, Tag, Tooltip, Typography } from 'antd';
import {
  EditOutlined,
  CheckOutlined,
  CloseOutlined,
  DeleteOutlined,
  RedoOutlined,
  ScissorOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import type { PlanningMessage } from '../../types/chat';

const { Text } = Typography;

const ROLE_COLORS: Record<string, string> = {
  user: 'blue',
  assistant: 'green',
  system: 'orange',
};

interface Props {
  message: PlanningMessage;
  onUpdate?: (id: string, updates: { role?: string; content?: string; included?: boolean }) => void;
  onDelete?: (id: string) => void;
  onReplay?: (msg: PlanningMessage) => void;
  onTruncateAndReplay?: (msg: PlanningMessage) => void;
  onCopyToArtifact?: (content: string) => void;
  isStreaming?: boolean;
}

export default function MessageBubble({
  message,
  onUpdate,
  onDelete,
  onReplay,
  onTruncateAndReplay,
  onCopyToArtifact,
  isStreaming,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [editRole, setEditRole] = useState(message.role);
  const [editContent, setEditContent] = useState(message.content);

  const handleSave = () => {
    onUpdate?.(message.id, { role: editRole, content: editContent });
    setEditing(false);
  };

  const handleCancel = () => {
    setEditRole(message.role);
    setEditContent(message.content);
    setEditing(false);
  };

  const isUser = message.role === 'user';

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start',
        marginBottom: 12,
      }}
    >
      {/* Header: role badge + metadata */}
      <Space size={4} style={{ marginBottom: 2 }}>
        <Tag color={ROLE_COLORS[message.role] || 'default'} style={{ margin: 0 }}>
          {message.role}
        </Tag>
        {message.agent_id && (
          <Text type="secondary" style={{ fontSize: 11 }}>
            {message.agent_id}
          </Text>
        )}
        {message.tokens != null && (
          <Text type="secondary" style={{ fontSize: 11 }}>
            {message.tokens} tokens
          </Text>
        )}
      </Space>

      {/* Content bubble */}
      <div
        style={{
          background: isUser ? '#e6f4ff' : '#f6ffed',
          borderRadius: 8,
          padding: '8px 12px',
          maxWidth: '80%',
          wordBreak: 'break-word',
        }}
      >
        {editing ? (
          <div>
            <Select
              value={editRole}
              onChange={setEditRole}
              size="small"
              style={{ width: 120, marginBottom: 4 }}
              options={[
                { label: 'User', value: 'user' },
                { label: 'Assistant', value: 'assistant' },
                { label: 'System', value: 'system' },
              ]}
            />
            <Input.TextArea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              autoSize={{ minRows: 2 }}
              style={{ marginBottom: 4 }}
            />
            <Space size={4}>
              <CheckOutlined onClick={handleSave} style={{ cursor: 'pointer', color: '#52c41a' }} />
              <CloseOutlined
                onClick={handleCancel}
                style={{ cursor: 'pointer', color: '#ff4d4f' }}
              />
            </Space>
          </div>
        ) : message.role === 'assistant' ? (
          <ReactMarkdown>{message.content}</ReactMarkdown>
        ) : (
          <span style={{ whiteSpace: 'pre-wrap' }}>{message.content}</span>
        )}
      </div>

      {/* Curation controls */}
      {onUpdate && !editing && (
        <Space size={8} style={{ marginTop: 2 }}>
          <Checkbox
            checked={message.included}
            onChange={(e) => onUpdate(message.id, { included: e.target.checked })}
          >
            <Text type="secondary" style={{ fontSize: 11 }}>
              Include
            </Text>
          </Checkbox>
          <EditOutlined
            onClick={() => setEditing(true)}
            style={{ cursor: 'pointer', fontSize: 12, color: '#8c8c8c' }}
          />
          {onDelete && (
            <DeleteOutlined
              onClick={() => onDelete(message.id)}
              style={{ cursor: 'pointer', fontSize: 12, color: '#ff4d4f' }}
            />
          )}
          {!isUser && onCopyToArtifact && (
            <Tooltip title="Copy to artifact">
              <CopyOutlined
                onClick={() => onCopyToArtifact(message.content)}
                style={{ cursor: 'pointer', fontSize: 12, color: '#722ed1' }}
              />
            </Tooltip>
          )}
          {isUser && onReplay && (
            <Tooltip title="Replay">
              <RedoOutlined
                onClick={() => !isStreaming && onReplay(message)}
                style={{
                  cursor: isStreaming ? 'not-allowed' : 'pointer',
                  fontSize: 12,
                  color: isStreaming ? '#d9d9d9' : '#1677ff',
                }}
              />
            </Tooltip>
          )}
          {isUser && onTruncateAndReplay && (
            <Tooltip title="Truncate & replay">
              <ScissorOutlined
                onClick={() => !isStreaming && onTruncateAndReplay(message)}
                style={{
                  cursor: isStreaming ? 'not-allowed' : 'pointer',
                  fontSize: 12,
                  color: isStreaming ? '#d9d9d9' : '#fa8c16',
                }}
              />
            </Tooltip>
          )}
        </Space>
      )}
    </div>
  );
}
