import { memo, useState } from 'react';
import {
  Checkbox,
  Input,
  Select,
  Space,
  Tag,
  Tooltip,
  Typography,
  Popover,
  Form,
  Button,
  message as antdMessage,
} from 'antd';
import {
  EditOutlined,
  CheckOutlined,
  CloseOutlined,
  DeleteOutlined,
  RedoOutlined,
  ScissorOutlined,
  CopyOutlined,
  LikeOutlined,
  DislikeOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import type { ChatMessage } from '../../types/chat';
import { useCreateFlagMutation } from '../../hooks/useTrainingQueries';
import type { FlagCreate } from '../../types/training';
import type { AnnotationCategory, FlagType } from '../../types/enums';

const { Text } = Typography;

const ROLE_COLORS: Record<string, string> = {
  user: 'blue',
  assistant: 'green',
  system: 'orange',
  tool_call: 'purple',
  tool_result: 'cyan',
};

const ANNOTATION_CATEGORIES: AnnotationCategory[] = [
  'style', 'accuracy', 'completeness', 'format', 'instruction_following', 'other',
];

interface Props {
  message: ChatMessage;
  messageIndex: number;
  sessionId: string;
  onUpdate?: (id: string, updates: { role?: string; content?: string; included?: boolean }) => void;
  onDelete?: (id: string) => void;
  onReplay?: (msg: ChatMessage) => void;
  onTruncate?: (msg: ChatMessage) => void;
  onCopyToArtifact?: (content: string) => void;
  isStreaming?: boolean;
}

function MessageBubbleInner({
  message,
  messageIndex,
  sessionId,
  onUpdate,
  onDelete,
  onReplay,
  onTruncate,
  onCopyToArtifact,
  isStreaming,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [editRole, setEditRole] = useState(message.role);
  const [editContent, setEditContent] = useState(message.content);

  // Training feedback state
  const [flagPopoverOpen, setFlagPopoverOpen] = useState(false);
  const [flagType, setFlagType] = useState<FlagType>('positive');
  const [flagCategory, setFlagCategory] = useState<AnnotationCategory | undefined>(undefined);
  const [flagNote, setFlagNote] = useState('');
  const createFlag = useCreateFlagMutation();

  const handleSave = () => {
    onUpdate?.(message.id, { role: editRole, content: editContent });
    setEditing(false);
  };

  const handleCancel = () => {
    setEditRole(message.role);
    setEditContent(message.content);
    setEditing(false);
  };

  const handleFlag = (type: FlagType) => {
    setFlagType(type);
    setFlagPopoverOpen(true);
  };

  const submitFlag = async () => {
    const data: FlagCreate = {
      session_ref: sessionId,
      message_index: messageIndex,
      flag_type: flagType,
      annotation_category: flagCategory,
      note: flagNote || undefined,
    };
    try {
      await createFlag.mutateAsync(data);
      antdMessage.success('Feedback recorded');
      setFlagPopoverOpen(false);
      setFlagNote('');
      setFlagCategory(undefined);
    } catch {
      antdMessage.error('Failed to save feedback');
    }
  };

  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';
  const isToolCall = message.role === 'tool_call';
  const isToolResult = message.role === 'tool_result';
  const isToolMessage = isToolCall || isToolResult;

  const flagContent = (
    <div style={{ width: 260 }}>
      <Form layout="vertical" size="small">
        <Form.Item label="Category" style={{ marginBottom: 8 }}>
          <Select
            placeholder="Optional category"
            allowClear
            value={flagCategory}
            onChange={setFlagCategory}
            options={ANNOTATION_CATEGORIES.map((cat) => ({ label: cat, value: cat }))}
          />
        </Form.Item>
        <Form.Item label="Note" style={{ marginBottom: 8 }}>
          <Input.TextArea
            rows={2}
            value={flagNote}
            onChange={(e) => setFlagNote(e.target.value)}
            placeholder="Optional note..."
          />
        </Form.Item>
        <Button type="primary" size="small" onClick={submitFlag} loading={createFlag.isPending} block>
          Submit
        </Button>
      </Form>
    </div>
  );

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
          background: isUser
            ? '#e6f4ff'
            : isToolCall
              ? '#f9f0ff'
              : isToolResult
                ? '#e6fffb'
                : '#f6ffed',
          borderRadius: 8,
          padding: '8px 12px',
          maxWidth: '80%',
          wordBreak: 'break-word',
          opacity: message.included ? 1 : 0.5,
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
        ) : isToolCall ? (
          <div>
            <Tag color="purple">{message.tool_name || 'tool'}</Tag>
            <pre style={{ fontSize: 11, margin: '4px 0 0', whiteSpace: 'pre-wrap' }}>
              {message.content}
            </pre>
          </div>
        ) : isToolResult ? (
          <div>
            <Tag color="cyan">{message.tool_name || 'result'}</Tag>
            <pre
              style={{
                fontSize: 11,
                margin: '4px 0 0',
                whiteSpace: 'pre-wrap',
                maxHeight: 200,
                overflow: 'auto',
              }}
            >
              {message.content}
            </pre>
          </div>
        ) : isAssistant ? (
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
          {!isToolMessage && (
            <EditOutlined
              onClick={() => setEditing(true)}
              style={{ cursor: 'pointer', fontSize: 12, color: '#8c8c8c' }}
            />
          )}
          {onDelete && (
            <DeleteOutlined
              onClick={() => onDelete(message.id)}
              style={{ cursor: 'pointer', fontSize: 12, color: '#ff4d4f' }}
            />
          )}
          {isAssistant && onCopyToArtifact && (
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
          {isUser && onTruncate && (
            <Tooltip title="Truncate & edit">
              <ScissorOutlined
                onClick={() => !isStreaming && onTruncate(message)}
                style={{
                  cursor: isStreaming ? 'not-allowed' : 'pointer',
                  fontSize: 12,
                  color: isStreaming ? '#d9d9d9' : '#fa8c16',
                }}
              />
            </Tooltip>
          )}
          {/* Training feedback (assistant only) */}
          {isAssistant && (
            <>
              <Popover
                content={flagContent}
                title={flagType === 'positive' ? 'Positive Feedback' : 'Negative Feedback'}
                trigger="click"
                open={flagPopoverOpen}
                onOpenChange={setFlagPopoverOpen}
              >
                <Tooltip title="Good response">
                  <LikeOutlined
                    onClick={() => handleFlag('positive')}
                    style={{ cursor: 'pointer', fontSize: 12, color: '#52c41a' }}
                  />
                </Tooltip>
              </Popover>
              <Tooltip title="Poor response">
                <DislikeOutlined
                  onClick={() => handleFlag('negative')}
                  style={{ cursor: 'pointer', fontSize: 12, color: '#ff4d4f' }}
                />
              </Tooltip>
            </>
          )}
        </Space>
      )}
    </div>
  );
}

const MessageBubble = memo(MessageBubbleInner);
export default MessageBubble;
