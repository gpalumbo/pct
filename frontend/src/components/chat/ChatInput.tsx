import { useState } from 'react';
import { Input, Button, Select, Space } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import { useProject } from '../../hooks/useConfigQueries';
import type { Agent } from '../../types/config';

const { TextArea } = Input;

interface ChatInputProps {
  onSend: (content: string) => void;
  isStreaming: boolean;
  selectedAgentId: string | null;
  onAgentChange: (agentId: string | null) => void;
}

export default function ChatInput({ onSend, isStreaming, selectedAgentId, onAgentChange }: ChatInputProps) {
  const [text, setText] = useState('');
  const { data: project } = useProject();
  const agents: Agent[] = project?.agents ?? [];

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={{ borderTop: '1px solid #f0f0f0', padding: '8px 0' }}>
      <Space.Compact style={{ width: '100%', display: 'flex', gap: 8 }}>
        <Select
          value={selectedAgentId}
          onChange={onAgentChange}
          placeholder="Agent"
          allowClear
          style={{ width: 140, flexShrink: 0 }}
        >
          {agents.map((a) => (
            <Select.Option key={a.id} value={a.id}>
              {a.name}
            </Select.Option>
          ))}
        </Select>
        <TextArea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message... (Enter to send, Shift+Enter for newline)"
          autoSize={{ minRows: 1, maxRows: 4 }}
          disabled={isStreaming}
          style={{ flex: 1 }}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleSend}
          loading={isStreaming}
          disabled={!text.trim()}
        >
          Send
        </Button>
      </Space.Compact>
    </div>
  );
}
