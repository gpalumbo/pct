import { useState } from 'react';
import { Typography, Button, Space, Tooltip, Popover, Form, Select, Input, message as antdMessage } from 'antd';
import {
  CheckCircleOutlined,
  MinusCircleOutlined,
  EditOutlined,
  DeleteOutlined,
  UserOutlined,
  RobotOutlined,
  LikeOutlined,
  DislikeOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import type { ChatMessage } from '../../types/chat';
import { useCreateFlagMutation } from '../../hooks/useTrainingQueries';
import type { FlagCreate } from '../../types/training';
import type { AnnotationCategory, FlagType } from '../../types/enums';

const { Text } = Typography;
const { TextArea } = Input;

const ANNOTATION_CATEGORIES: AnnotationCategory[] = [
  'style', 'accuracy', 'completeness', 'format', 'instruction_following', 'other',
];

interface MessageBubbleProps {
  message: ChatMessage;
  messageIndex: number;
  sessionId: string;
  onToggleInclude: (messageId: string, included: boolean) => void;
  onEdit?: (messageId: string) => void;
  onDelete: (messageId: string) => void;
}

export default function MessageBubble({ message, messageIndex, sessionId, onToggleInclude, onEdit, onDelete }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const isAssistant = message.role === 'assistant';
  const [flagPopoverOpen, setFlagPopoverOpen] = useState(false);
  const [flagType, setFlagType] = useState<FlagType>('positive');
  const [flagCategory, setFlagCategory] = useState<AnnotationCategory | undefined>(undefined);
  const [flagNote, setFlagNote] = useState('');
  const createFlag = useCreateFlagMutation();

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
          <TextArea
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
        marginBottom: 8,
        opacity: message.included ? 1 : 0.5,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>
        {isUser ? <UserOutlined style={{ fontSize: 11 }} /> : <RobotOutlined style={{ fontSize: 11 }} />}
        <Text type="secondary" style={{ fontSize: 11 }}>
          {message.role}
        </Text>
      </div>

      <div
        style={{
          maxWidth: '80%',
          padding: '8px 12px',
          borderRadius: 8,
          backgroundColor: isSystem ? '#fff7e6' : isUser ? '#e6f7ff' : '#f6ffed',
          border: `1px solid ${isSystem ? '#ffd591' : isUser ? '#91d5ff' : '#b7eb8f'}`,
          fontSize: 13,
        }}
      >
        <ReactMarkdown>{message.content}</ReactMarkdown>
      </div>

      <Space size={2} style={{ marginTop: 2 }}>
        <Tooltip title={message.included ? 'Exclude from context' : 'Include in context'}>
          <Button
            type="text"
            size="small"
            icon={message.included ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : <MinusCircleOutlined />}
            onClick={() => onToggleInclude(message.id, !message.included)}
          />
        </Tooltip>
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
                <Button
                  type="text"
                  size="small"
                  icon={<LikeOutlined style={{ color: '#52c41a' }} />}
                  onClick={() => handleFlag('positive')}
                />
              </Tooltip>
            </Popover>
            <Tooltip title="Poor response">
              <Button
                type="text"
                size="small"
                icon={<DislikeOutlined style={{ color: '#ff4d4f' }} />}
                onClick={() => handleFlag('negative')}
              />
            </Tooltip>
          </>
        )}
        {onEdit && (
          <Tooltip title="Edit">
            <Button type="text" size="small" icon={<EditOutlined />} onClick={() => onEdit(message.id)} />
          </Tooltip>
        )}
        <Tooltip title="Delete">
          <Button type="text" size="small" icon={<DeleteOutlined />} onClick={() => onDelete(message.id)} />
        </Tooltip>
      </Space>
    </div>
  );
}
