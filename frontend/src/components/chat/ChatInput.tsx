import { useState } from 'react';
import { Button, Input, Select, Space } from 'antd';
import { SendOutlined, StopOutlined } from '@ant-design/icons';
import { useAgents } from '../../hooks/useConfigQueries';

interface Props {
  isStreaming: boolean;
  onSend: (content: string, agentId: string | null) => void;
  onStop: () => void;
}

export default function ChatInput({ isStreaming, onSend, onStop }: Props) {
  const [content, setContent] = useState('');
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const { data: agents = [] } = useAgents();

  const handleSend = () => {
    const trimmed = content.trim();
    if (!trimmed) return;
    onSend(trimmed, selectedAgent);
    setContent('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isStreaming) handleSend();
    }
  };

  return (
    <div style={{ padding: '8px 16px 16px', borderTop: '1px solid #f0f0f0' }}>
      <Space.Compact style={{ width: '100%' }}>
        {agents.length > 0 && (
          <Select
            value={selectedAgent}
            onChange={setSelectedAgent}
            placeholder="Agent"
            allowClear
            style={{ width: 160 }}
            options={agents.map((a) => ({ label: `${a.id} (${a.model})`, value: a.id }))}
          />
        )}
        <Input.TextArea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message... (Enter to send, Shift+Enter for newline)"
          autoSize={{ minRows: 1, maxRows: 6 }}
          disabled={isStreaming}
          style={{ flex: 1 }}
        />
        {isStreaming ? (
          <Button icon={<StopOutlined />} danger onClick={onStop}>
            Stop
          </Button>
        ) : (
          <Button type="primary" icon={<SendOutlined />} onClick={handleSend} disabled={!content.trim()}>
            Send
          </Button>
        )}
      </Space.Compact>
    </div>
  );
}
