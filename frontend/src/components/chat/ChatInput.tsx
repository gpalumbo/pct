import { useState, useMemo } from 'react';
import { Button, Input, Select, Space } from 'antd';
import { SendOutlined, StopOutlined } from '@ant-design/icons';
import { useAgents, useProjectConfig, useWorkflowStages } from '../../hooks/useConfigQueries';

interface Props {
  isStreaming: boolean;
  onSend: (content: string, agentId: string | null) => void;
  onStop: () => void;
  selectedAgent: string | null;
  onAgentChange: (agentId: string | null) => void;
  /** Current task workflow stage (e.g. "draft"). Used to resolve stage-level default agent. */
  taskStage?: string;
}

export default function ChatInput({ isStreaming, onSend, onStop, selectedAgent, onAgentChange, taskStage }: Props) {
  const [content, setContent] = useState('');
  const { data: agents = [] } = useAgents();
  const { data: projectConfig } = useProjectConfig();
  const { data: workflowStages } = useWorkflowStages();

  // Resolve default agent: stage agent > project default_agent > planning_agent > first agent
  const defaultAgentId = useMemo(() => {
    if (taskStage && workflowStages) {
      const stage = workflowStages.find((s) => s.stage === taskStage);
      if (stage?.agent) return stage.agent;
    }
    if (projectConfig?.default_agent) return projectConfig.default_agent;
    if (projectConfig?.planning_agent) return projectConfig.planning_agent;
    if (agents.length > 0) return agents[0].id;
    return null;
  }, [taskStage, workflowStages, projectConfig, agents]);

  const effectiveAgent = selectedAgent ?? defaultAgentId;

  const handleSend = () => {
    const trimmed = content.trim();
    if (!trimmed) return;
    onSend(trimmed, effectiveAgent);
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
            onChange={onAgentChange}
            placeholder={defaultAgentId ? `Default: ${defaultAgentId}` : 'Agent'}
            allowClear
            style={{ width: 200 }}
            options={agents
              .filter((a) => a.provider_type !== 'user')
              .map((a) => ({
                label: a.id === defaultAgentId
                  ? `${a.id} (${a.model}) *`
                  : `${a.id} (${a.model})`,
                value: a.id,
              }))}
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
