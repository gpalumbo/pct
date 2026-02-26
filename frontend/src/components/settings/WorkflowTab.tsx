import { useEffect, useState, useCallback } from 'react';
import { Button, Input, Select, Space, Switch, Tooltip, Typography, message, Collapse } from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  HolderOutlined,
  CheckOutlined,
  UndoOutlined,
} from '@ant-design/icons';
import { DragDropContext, Droppable, Draggable, type DropResult } from '@hello-pangea/dnd';
import {
  useWorkflowStages,
  useSaveWorkflowStages,
  useAgents,
  useTemplateVariables,
  useSaveTemplateVariables,
} from '../../hooks/useConfigQueries';
import type { WorkflowStageConfig, TemplateVariable } from '../../types/config';

const { Text } = Typography;
const { TextArea } = Input;

function slugify(label: string): string {
  return label
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

/** Built-in variables resolved dynamically at runtime (read-only reference). */
const BUILTIN_VARS: { key: string; description: string }[] = [
  { key: 'artifact', description: 'Full content of the task artifact file' },
  { key: 'artifact_path', description: 'Directory path to the task artifact folder' },
  {
    key: 'artifact_main_path',
    description: 'Path to the main text file (e.g. main.md) inside the artifact directory',
  },
  { key: 'task_title', description: "The task's title" },
  { key: 'feature_title', description: "The parent feature's title" },
  { key: 'cross_refs', description: 'Cross-reference context from wikilinks' },
];

export default function WorkflowTab() {
  const { data: savedStages = [] } = useWorkflowStages();
  const { data: agents = [] } = useAgents();
  const saveStages = useSaveWorkflowStages();

  const { data: savedVars = [] } = useTemplateVariables();
  const saveVars = useSaveTemplateVariables();

  const [stages, setStages] = useState<WorkflowStageConfig[]>([]);
  const [editState, setEditState] = useState<Record<number, { label: string; prompt: string }>>({});

  const [customVars, setCustomVars] = useState<TemplateVariable[]>([]);

  useEffect(() => {
    setStages(savedStages);
    setEditState({});
  }, [savedStages]);

  useEffect(() => {
    setCustomVars(savedVars);
  }, [savedVars]);

  // --- Stage helpers ---

  const updateStage = (index: number, patch: Partial<WorkflowStageConfig>) => {
    setStages((prev) => prev.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  };

  const addStage = () => {
    const label = 'New Stage';
    let id = slugify(label);
    const existing = new Set(stages.map((s) => s.stage));
    let counter = 1;
    while (existing.has(id)) {
      id = slugify(label) + '-' + counter++;
    }
    setStages((prev) => [
      ...prev,
      { stage: id, label, enabled: true, agent: null, prompt_template: '' },
    ]);
  };

  const removeStage = (index: number) => {
    setStages((prev) => prev.filter((_, i) => i !== index));
    setEditState((prev) => {
      const next = { ...prev };
      delete next[index];
      return next;
    });
  };

  const handleSave = async () => {
    await saveStages.mutateAsync(stages);
    message.success('Workflow stages saved');
  };

  const handleLabelChange = (index: number, newLabel: string) => {
    const stage = stages[index];
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

  // --- Edit tracking helpers ---
  const getEditValue = (index: number, field: 'label' | 'prompt') => {
    return editState[index]?.[field];
  };

  const startEdit = (index: number, field: 'label' | 'prompt', value: string) => {
    setEditState((prev) => ({
      ...prev,
      [index]: {
        ...(prev[index] ?? {
          label: stages[index].label,
          prompt: stages[index].prompt_template || '',
        }),
        [field]: value,
      },
    }));
  };

  const isDirty = useCallback(
    (index: number) => {
      const edit = editState[index];
      if (!edit) return false;
      const stage = stages[index];
      if (!stage) return false;
      return edit.label !== stage.label || edit.prompt !== (stage.prompt_template || '');
    },
    [editState, stages],
  );

  const commitEdit = (index: number) => {
    const edit = editState[index];
    if (!edit) return;
    handleLabelChange(index, edit.label);
    updateStage(index, { prompt_template: edit.prompt });
    setEditState((prev) => {
      const next = { ...prev };
      delete next[index];
      return next;
    });
  };

  const cancelEdit = (index: number) => {
    setEditState((prev) => {
      const next = { ...prev };
      delete next[index];
      return next;
    });
  };

  const ensureEdit = (index: number) => {
    if (editState[index] == null) {
      const stage = stages[index];
      setEditState((prev) => ({
        ...prev,
        [index]: { label: stage.label, prompt: stage.prompt_template || '' },
      }));
    }
  };

  // --- Drag and drop ---
  const onDragEnd = (result: DropResult) => {
    if (!result.destination) return;
    const from = result.source.index;
    const to = result.destination.index;
    if (from === to) return;
    setStages((prev) => {
      const next = [...prev];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      return next;
    });
    setEditState({});
  };

  // --- Template variable helpers ---
  const addCustomVar = () => {
    setCustomVars((prev) => [...prev, { key: '', description: '', value: '' }]);
  };

  const updateCustomVar = (index: number, patch: Partial<TemplateVariable>) => {
    setCustomVars((prev) => prev.map((v, i) => (i === index ? { ...v, ...patch } : v)));
  };

  const removeCustomVar = (index: number) => {
    setCustomVars((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSaveVars = async () => {
    await saveVars.mutateAsync(customVars);
    message.success('Template variables saved');
  };

  return (
    <div>
      {/* Header row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '32px minmax(0, 320px) 2fr 60px 200px 70px',
          gap: 8,
          alignItems: 'center',
          padding: '4px 8px',
          fontWeight: 600,
          fontSize: 13,
          color: '#888',
          borderBottom: '1px solid #303030',
        }}
      >
        <div></div>
        <div>Name</div>
        <div>Prompt</div>
        <div>Enabled</div>
        <div>Agent</div>
        <div></div>
      </div>

      <DragDropContext onDragEnd={onDragEnd}>
        <Droppable droppableId="workflow-stages">
          {(provided) => (
            <div
              ref={provided.innerRef}
              {...provided.droppableProps}
              style={{ display: 'flex', flexDirection: 'column' }}
            >
              {stages.map((stage, index) => {
                const editLabel = getEditValue(index, 'label') ?? stage.label;
                const editPrompt = getEditValue(index, 'prompt') ?? (stage.prompt_template || '');
                const dirty = isDirty(index);

                return (
                  <Draggable
                    key={stage.stage + '-' + index}
                    draggableId={stage.stage + '-' + index}
                    index={index}
                  >
                    {(dragProvided, snapshot) => (
                      <div
                        ref={dragProvided.innerRef}
                        {...dragProvided.draggableProps}
                        style={{
                          ...dragProvided.draggableProps.style,
                          display: 'grid',
                          gridTemplateColumns: '32px minmax(0, 320px) 2fr 60px 200px 70px',
                          gap: 8,
                          alignItems: 'center',
                          padding: '6px 8px',
                          borderBottom: '1px solid #222',
                          background: snapshot.isDragging ? '#1a1a2e' : undefined,
                          userSelect: 'none',
                        }}
                      >
                        {/* Drag handle */}
                        <div
                          {...dragProvided.dragHandleProps}
                          style={{
                            cursor: 'grab',
                            color: '#666',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                        >
                          <HolderOutlined style={{ fontSize: 16 }} />
                        </div>

                        {/* Name — always editable */}
                        <Input
                          size="small"
                          value={editLabel}
                          maxLength={50}
                          onChange={(e) => {
                            ensureEdit(index);
                            startEdit(index, 'label', e.target.value);
                          }}
                          placeholder="Stage name"
                          style={{ width: '100%' }}
                        />

                        {/* Prompt — always editable */}
                        <TextArea
                          size="small"
                          autoSize={{ minRows: 1, maxRows: 4 }}
                          value={editPrompt}
                          onChange={(e) => {
                            ensureEdit(index);
                            startEdit(index, 'prompt', e.target.value);
                          }}
                          placeholder="Prompt template (optional)"
                          style={{ fontSize: 12, width: '100%' }}
                        />

                        {/* Enabled toggle */}
                        <div style={{ display: 'flex', justifyContent: 'center' }}>
                          <Switch
                            size="small"
                            checked={stage.enabled}
                            onChange={(v) => updateStage(index, { enabled: v })}
                            style={{ minWidth: 28 }}
                          />
                        </div>

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

                        {/* Actions: cancel/save when dirty, delete when clean */}
                        <div style={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
                          {dirty ? (
                            <>
                              <Tooltip title="Save edits">
                                <Button
                                  type="text"
                                  size="small"
                                  icon={<CheckOutlined />}
                                  onClick={() => commitEdit(index)}
                                  style={{ color: '#52c41a' }}
                                />
                              </Tooltip>
                              <Tooltip title="Cancel edits">
                                <Button
                                  type="text"
                                  size="small"
                                  icon={<UndoOutlined />}
                                  onClick={() => cancelEdit(index)}
                                />
                              </Tooltip>
                            </>
                          ) : (
                            <Tooltip title="Remove stage">
                              <Button
                                type="text"
                                size="small"
                                danger
                                icon={<DeleteOutlined />}
                                onClick={() => removeStage(index)}
                              />
                            </Tooltip>
                          )}
                        </div>
                      </div>
                    )}
                  </Draggable>
                );
              })}
              {provided.placeholder}
            </div>
          )}
        </Droppable>
      </DragDropContext>

      <Space style={{ marginTop: 16 }}>
        <Button icon={<PlusOutlined />} onClick={addStage}>
          Add Stage
        </Button>
        <Button type="primary" onClick={handleSave} loading={saveStages.isPending}>
          Save Changes
        </Button>
      </Space>

      {/* Template Variables */}
      <Collapse
        ghost
        style={{ marginTop: 24 }}
        items={[
          {
            key: 'template-vars',
            label: (
              <Text strong style={{ fontSize: 14 }}>
                Template Variables
              </Text>
            ),
            children: (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {/* Built-in variables (read-only reference) */}
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Built-in variables (resolved at runtime):
                </Text>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginBottom: 8 }}>
                  {BUILTIN_VARS.map((v) => (
                    <div
                      key={v.key}
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '160px 1fr',
                        gap: 8,
                        alignItems: 'center',
                        padding: '2px 0',
                      }}
                    >
                      <code style={{ fontSize: 12, color: '#1890ff' }}>{`{{${v.key}}}`}</code>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {v.description}
                      </Text>
                    </div>
                  ))}
                </div>

                {/* Custom variables (editable) */}
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Custom variables (static text substituted into prompts):
                </Text>

                {/* Header */}
                {customVars.length > 0 && (
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '140px 1fr 2fr 32px',
                      gap: 8,
                      padding: '2px 0',
                      fontWeight: 600,
                      fontSize: 12,
                      color: '#888',
                    }}
                  >
                    <div>Key</div>
                    <div>Description</div>
                    <div>Value</div>
                    <div></div>
                  </div>
                )}

                {customVars.map((v, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '140px 1fr 2fr 32px',
                      gap: 8,
                      alignItems: 'center',
                    }}
                  >
                    <Input
                      size="small"
                      value={v.key}
                      onChange={(e) =>
                        updateCustomVar(i, {
                          key: e.target.value.replace(/[^a-z0-9_]/gi, '_').toLowerCase(),
                        })
                      }
                      placeholder="variable_name"
                      style={{ fontFamily: 'monospace', fontSize: 12 }}
                    />
                    <Input
                      size="small"
                      value={v.description}
                      onChange={(e) => updateCustomVar(i, { description: e.target.value })}
                      placeholder="Description"
                      style={{ fontSize: 12 }}
                    />
                    <TextArea
                      size="small"
                      autoSize={{ minRows: 1, maxRows: 3 }}
                      value={v.value}
                      onChange={(e) => updateCustomVar(i, { value: e.target.value })}
                      placeholder="Value text"
                      style={{ fontSize: 12 }}
                    />
                    <Tooltip title="Remove">
                      <Button
                        type="text"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => removeCustomVar(i)}
                      />
                    </Tooltip>
                  </div>
                ))}

                <Space style={{ marginTop: 4 }}>
                  <Button size="small" icon={<PlusOutlined />} onClick={addCustomVar}>
                    Add Variable
                  </Button>
                  <Button
                    size="small"
                    type="primary"
                    onClick={handleSaveVars}
                    loading={saveVars.isPending}
                  >
                    Save Variables
                  </Button>
                </Space>
              </div>
            ),
          },
        ]}
      />
    </div>
  );
}
