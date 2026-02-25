import { useEffect, useState } from 'react';
import { Button, Input, Select, Space, Switch, Tooltip, Typography, message } from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  UpOutlined,
  DownOutlined,
  EditOutlined,
} from '@ant-design/icons';
import { useWorkflowStages, useSaveWorkflowStages, useAgents } from '../../hooks/useConfigQueries';
import type { WorkflowStageConfig } from '../../types/config';

const { Text } = Typography;
const { TextArea } = Input;

function slugify(label: string): string {
  return label
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

export default function WorkflowTab() {
  const { data: savedStages = [] } = useWorkflowStages();
  const { data: agents = [] } = useAgents();
  const saveStages = useSaveWorkflowStages();

  const [stages, setStages] = useState<WorkflowStageConfig[]>([]);
  const [expandedPrompt, setExpandedPrompt] = useState<string | null>(null);

  useEffect(() => {
    setStages(savedStages);
  }, [savedStages]);

  const updateStage = (index: number, patch: Partial<WorkflowStageConfig>) => {
    setStages((prev) => prev.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  };

  const addStage = () => {
    const label = 'New Stage';
    let id = slugify(label);
    // Ensure unique id
    const existing = new Set(stages.map((s) => s.stage));
    let counter = 1;
    while (existing.has(id)) {
      id = slugify(label) + '-' + counter++;
    }
    setStages((prev) => [...prev, { stage: id, label, enabled: true, agent: null, prompt_template: '' }]);
  };

  const removeStage = (index: number) => {
    setStages((prev) => prev.filter((_, i) => i !== index));
    setExpandedPrompt(null);
  };

  const moveStage = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= stages.length) return;
    setStages((prev) => {
      const next = [...prev];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  };

  const handleSave = async () => {
    await saveStages.mutateAsync(stages);
    message.success('Workflow stages saved');
  };

  const handleLabelChange = (index: number, newLabel: string) => {
    const stage = stages[index];
    // If the stage ID was auto-generated from the old label (or is "new-stage*"), update it
    const oldSlug = slugify(stage.label);
    const isAutoId = stage.stage === oldSlug || stage.stage.startsWith('new-stage');
    const patch: Partial<WorkflowStageConfig> = { label: newLabel };
    if (isAutoId) {
      const newSlug = slugify(newLabel);
      const existing = new Set(stages.filter((_, i) => i !== index).map((s) => s.stage));
      if (newSlug && !existing.has(newSlug)) {
        patch.stage = newSlug;
      }
    }
    updateStage(index, patch);
  };

  return (
    <div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {/* Header row */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '40px 1fr 70px 200px 80px',
            gap: 8,
            alignItems: 'center',
            padding: '4px 8px',
            fontWeight: 600,
            fontSize: 13,
            color: '#888',
            borderBottom: '1px solid #303030',
          }}
        >
          <div>Order</div>
          <div>Stage</div>
          <div>Enabled</div>
          <div>Agent</div>
          <div></div>
        </div>

        {stages.map((stage, index) => (
          <div key={stage.stage + '-' + index}>
            {/* Main row */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '40px 1fr 70px 200px 80px',
                gap: 8,
                alignItems: 'center',
                padding: '4px 8px',
                borderBottom: '1px solid #222',
                background: expandedPrompt === stage.stage ? '#1a1a2e' : undefined,
              }}
            >
              {/* Reorder buttons */}
              <Space direction="vertical" size={0}>
                <Tooltip title="Move up">
                  <Button
                    type="text"
                    size="small"
                    icon={<UpOutlined />}
                    disabled={index === 0}
                    onClick={() => moveStage(index, -1)}
                    style={{ padding: '0 4px', height: 20 }}
                  />
                </Tooltip>
                <Tooltip title="Move down">
                  <Button
                    type="text"
                    size="small"
                    icon={<DownOutlined />}
                    disabled={index === stages.length - 1}
                    onClick={() => moveStage(index, 1)}
                    style={{ padding: '0 4px', height: 20 }}
                  />
                </Tooltip>
              </Space>

              {/* Label (editable) */}
              <Space>
                <Input
                  size="small"
                  value={stage.label}
                  onChange={(e) => handleLabelChange(index, e.target.value)}
                  style={{ width: 160 }}
                />
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {stage.stage}
                </Text>
                <Tooltip title="Edit prompt template">
                  <Button
                    type="text"
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() =>
                      setExpandedPrompt(expandedPrompt === stage.stage ? null : stage.stage)
                    }
                    style={{
                      color: stage.prompt_template ? '#1890ff' : undefined,
                    }}
                  />
                </Tooltip>
              </Space>

              {/* Enabled toggle */}
              <Switch
                size="small"
                checked={stage.enabled}
                onChange={(v) => updateStage(index, { enabled: v })}
              />

              {/* Agent selector */}
              <Select
                allowClear
                size="small"
                style={{ width: '100%' }}
                value={stage.agent}
                onChange={(v) => updateStage(index, { agent: v ?? null })}
                options={agents.map((a) => ({ label: a.id, value: a.id }))}
                placeholder="Select agent"
              />

              {/* Delete button */}
              <Tooltip title="Remove stage">
                <Button
                  type="text"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => removeStage(index)}
                />
              </Tooltip>
            </div>

            {/* Expanded prompt editor */}
            {expandedPrompt === stage.stage && (
              <div style={{ padding: '8px 8px 8px 56px', background: '#1a1a2e' }}>
                <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 4 }}>
                  Stage prompt template — Available variables:{' '}
                  <code>{'{{artifact}}'}</code>, <code>{'{{artifact_path}}'}</code>,{' '}
                  <code>{'{{task_title}}'}</code>, <code>{'{{feature_title}}'}</code>,{' '}
                  <code>{'{{cross_refs}}'}</code>
                </Text>
                <TextArea
                  rows={3}
                  value={stage.prompt_template || ''}
                  onChange={(e) => updateStage(index, { prompt_template: e.target.value })}
                  placeholder="e.g. Review {{artifact}} for quality. Cross-check against {{cross_refs}}."
                  style={{ fontSize: 12 }}
                />
              </div>
            )}
          </div>
        ))}
      </div>

      <Space style={{ marginTop: 16 }}>
        <Button icon={<PlusOutlined />} onClick={addStage}>
          Add Stage
        </Button>
        <Button
          type="primary"
          onClick={handleSave}
          loading={saveStages.isPending}
        >
          Save Changes
        </Button>
      </Space>
    </div>
  );
}
