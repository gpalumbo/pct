import { useState, useCallback } from 'react';
import {
  Typography,
  Button,
  Space,
  Switch,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  Popconfirm,
  Tooltip,
  message,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  HolderOutlined,
} from '@ant-design/icons';
import {
  DragDropContext,
  Droppable,
  Draggable,
  type DropResult,
} from '@hello-pangea/dnd';
import { useProject, useUpdateProject } from '../../hooks/useConfigQueries';
import type { WorkflowStage, Project } from '../../types/config';
import { toSlug } from '../../utils/slug';

const { Title, Text } = Typography;

interface StageFormValues {
  label: string;
  enabled: boolean;
  agent_id: string | null;
  prompt_template: string | null;
  auto_run: boolean;
}

export default function WorkflowTab() {
  const { data: project } = useProject();
  const updateProject = useUpdateProject();

  const stages: WorkflowStage[] = (project?.workflow_stages ?? [])
    .slice()
    .sort((a, b) => a.sort_order - b.sort_order);
  const agents = project?.agents ?? [];

  const [modalOpen, setModalOpen] = useState(false);
  const [editingStage, setEditingStage] = useState<WorkflowStage | null>(null);
  const [form] = Form.useForm<StageFormValues>();

  const saveStages = useCallback(
    (newStages: WorkflowStage[]) => {
      if (!project) return;
      const updated: Project = { ...project, workflow_stages: newStages };
      updateProject.mutate(updated, {
        onError: () => message.error('Failed to save workflow stages'),
      });
    },
    [project, updateProject],
  );

  // --- Drag and drop ---
  const onDragEnd = useCallback(
    (result: DropResult) => {
      if (!result.destination) return;
      const srcIdx = result.source.index;
      const destIdx = result.destination.index;
      if (srcIdx === destIdx) return;

      const reordered = [...stages];
      const [moved] = reordered.splice(srcIdx, 1);
      reordered.splice(destIdx, 0, moved);

      // Reassign sort_order based on new positions
      const updated = reordered.map((s, i) => ({ ...s, sort_order: i }));
      saveStages(updated);
    },
    [stages, saveStages],
  );

  // --- Toggle handlers ---
  const handleToggle = useCallback(
    (stageId: string, field: 'enabled' | 'auto_run', value: boolean) => {
      const updated = stages.map((s) =>
        s.id === stageId ? { ...s, [field]: value } : s,
      );
      saveStages(updated);
    },
    [stages, saveStages],
  );

  // --- Add / Edit ---
  const openAddModal = useCallback(() => {
    setEditingStage(null);
    form.resetFields();
    form.setFieldsValue({
      label: '',
      enabled: true,
      agent_id: null,
      prompt_template: null,
      auto_run: false,
    });
    setModalOpen(true);
  }, [form]);

  const openEditModal = useCallback(
    (stage: WorkflowStage) => {
      setEditingStage(stage);
      form.setFieldsValue({
        label: stage.label,
        enabled: stage.enabled,
        agent_id: stage.agent_id ?? null,
        prompt_template: stage.prompt_template ?? null,
        auto_run: stage.auto_run,
      });
      setModalOpen(true);
    },
    [form],
  );

  const handleModalOk = useCallback(() => {
    form
      .validateFields()
      .then((values) => {
        if (editingStage) {
          // Edit existing
          const updated = stages.map((s) =>
            s.id === editingStage.id
              ? {
                  ...s,
                  label: values.label,
                  enabled: values.enabled,
                  agent_id: values.agent_id || null,
                  prompt_template: values.prompt_template || null,
                  auto_run: values.auto_run,
                }
              : s,
          );
          saveStages(updated);
        } else {
          // Add new
          const newId = toSlug(values.label);
          if (stages.some((s) => s.id === newId)) {
            message.error(`Stage "${newId}" already exists`);
            return;
          }
          const newStage: WorkflowStage = {
            id: newId,
            label: values.label,
            enabled: values.enabled,
            agent_id: values.agent_id || null,
            prompt_template: values.prompt_template || null,
            auto_run: values.auto_run,
            sort_order: stages.length,
          };
          saveStages([...stages, newStage]);
        }
        setModalOpen(false);
        setEditingStage(null);
        form.resetFields();
      })
      .catch(() => {
        // validation failed, form will show errors
      });
  }, [form, editingStage, stages, saveStages]);

  const handleModalCancel = useCallback(() => {
    setModalOpen(false);
    setEditingStage(null);
    form.resetFields();
  }, [form]);

  // --- Delete ---
  const handleDelete = useCallback(
    (stageId: string) => {
      const filtered = stages
        .filter((s) => s.id !== stageId)
        .map((s, i) => ({ ...s, sort_order: i }));
      saveStages(filtered);
    },
    [stages, saveStages],
  );

  // --- Agent name lookup ---
  const agentName = useCallback(
    (agentId: string | null | undefined): string => {
      if (!agentId) return '';
      const agent = agents.find((a) => a.id === agentId);
      return agent?.name ?? agentId;
    },
    [agents],
  );

  return (
    <div>
      <Space
        style={{
          marginBottom: 16,
          display: 'flex',
          justifyContent: 'space-between',
        }}
      >
        <Title level={5} style={{ margin: 0 }}>
          Workflow Stages
        </Title>
        <Button icon={<PlusOutlined />} type="primary" onClick={openAddModal}>
          Add Stage
        </Button>
      </Space>

      {stages.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Text type="secondary">No workflow stages defined</Text>
        </div>
      ) : (
        <DragDropContext onDragEnd={onDragEnd}>
          <Droppable droppableId="workflow-stages">
            {(provided) => (
              <div ref={provided.innerRef} {...provided.droppableProps}>
                {/* Table header */}
                <div
                  className="pct-col-header"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '8px 12px',
                    borderBottom: '1px solid var(--pct-color-border-light)',
                  }}
                >
                  <div style={{ width: 36 }} />
                  <div style={{ flex: 2, minWidth: 120 }}>Label</div>
                  <div style={{ width: 80, textAlign: 'center' }}>Enabled</div>
                  <div style={{ flex: 1, minWidth: 100 }}>Agent</div>
                  <div style={{ width: 80, textAlign: 'center' }}>Auto Run</div>
                  <div style={{ flex: 2, minWidth: 120 }}>Prompt Template</div>
                  <div style={{ width: 80, textAlign: 'center' }}>Actions</div>
                </div>

                {/* Draggable rows */}
                {stages.map((stage, index) => (
                  <Draggable
                    key={stage.id}
                    draggableId={stage.id}
                    index={index}
                  >
                    {(dragProvided, snapshot) => (
                      <div
                        ref={dragProvided.innerRef}
                        {...dragProvided.draggableProps}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          padding: '10px 12px',
                          borderBottom: '1px solid var(--pct-color-border-light)',
                          background: snapshot.isDragging
                            ? 'var(--pct-bubble-user)'
                            : '#fff',
                          boxShadow: snapshot.isDragging
                            ? '0 2px 8px rgba(0,0,0,0.15)'
                            : 'none',
                          borderRadius: snapshot.isDragging ? 6 : 0,
                          transition: 'background 0.2s',
                          ...dragProvided.draggableProps.style,
                        }}
                      >
                        {/* Drag handle */}
                        <div
                          {...dragProvided.dragHandleProps}
                          style={{
                            width: 36,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            cursor: 'grab',
                            color: 'var(--pct-color-text-disabled)',
                          }}
                        >
                          <HolderOutlined className="pct-text-xl" />
                        </div>

                        {/* Label */}
                        <div style={{ flex: 2, minWidth: 120, fontWeight: 500 }}>
                          {stage.label}
                        </div>

                        {/* Enabled */}
                        <div style={{ width: 80, textAlign: 'center' }}>
                          <Switch
                            size="small"
                            checked={stage.enabled}
                            onChange={(checked) =>
                              handleToggle(stage.id, 'enabled', checked)
                            }
                          />
                        </div>

                        {/* Agent */}
                        <div style={{ flex: 1, minWidth: 100 }}>
                          {stage.agent_id ? (
                            <Tag color="blue">{agentName(stage.agent_id)}</Tag>
                          ) : (
                            <Tag color="default">None</Tag>
                          )}
                        </div>

                        {/* Auto Run */}
                        <div style={{ width: 80, textAlign: 'center' }}>
                          <Switch
                            size="small"
                            checked={stage.auto_run}
                            onChange={(checked) =>
                              handleToggle(stage.id, 'auto_run', checked)
                            }
                          />
                        </div>

                        {/* Prompt Template (truncated) */}
                        <div style={{ flex: 2, minWidth: 120 }}>
                          {stage.prompt_template ? (
                            <Tooltip title={stage.prompt_template}>
                              <Text
                                ellipsis
                                className="pct-text-base"
                                style={{
                                  maxWidth: '100%',
                                  display: 'inline-block',
                                  color: 'var(--pct-color-text-secondary)',
                                }}
                              >
                                {stage.prompt_template}
                              </Text>
                            </Tooltip>
                          ) : (
                            <Text type="secondary" className="pct-text-base">
                              --
                            </Text>
                          )}
                        </div>

                        {/* Actions */}
                        <div style={{ width: 80, textAlign: 'center' }}>
                          <Space size={4}>
                            <Tooltip title="Edit">
                              <Button
                                type="text"
                                size="small"
                                icon={<EditOutlined />}
                                onClick={() => openEditModal(stage)}
                              />
                            </Tooltip>
                            <Popconfirm
                              title="Delete this stage?"
                              description={`"${stage.label}" will be permanently removed.`}
                              onConfirm={() => handleDelete(stage.id)}
                              okText="Delete"
                              okButtonProps={{ danger: true }}
                              cancelText="Cancel"
                            >
                              <Tooltip title="Delete">
                                <Button
                                  type="text"
                                  size="small"
                                  danger
                                  icon={<DeleteOutlined />}
                                />
                              </Tooltip>
                            </Popconfirm>
                          </Space>
                        </div>
                      </div>
                    )}
                  </Draggable>
                ))}
                {provided.placeholder}
              </div>
            )}
          </Droppable>
        </DragDropContext>
      )}

      {/* Add / Edit Modal */}
      <Modal
        title={editingStage ? 'Edit Workflow Stage' : 'Add Workflow Stage'}
        open={modalOpen}
        onOk={handleModalOk}
        onCancel={handleModalCancel}
        okText={editingStage ? 'Save' : 'Add'}
        confirmLoading={updateProject.isPending}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            label: '',
            enabled: true,
            agent_id: null,
            prompt_template: null,
            auto_run: false,
          }}
        >
          <Form.Item
            name="label"
            label="Label"
            rules={[
              { required: true, message: 'Stage label is required' },
              { max: 100, message: 'Label must be 100 characters or fewer' },
            ]}
          >
            <Input placeholder="e.g. Code Review" />
          </Form.Item>

          <Form.Item
            name="enabled"
            label="Enabled"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item name="agent_id" label="Agent">
            <Select
              placeholder="Select an agent (optional)"
              allowClear
              options={agents.map((a) => ({
                label: a.name,
                value: a.id,
              }))}
            />
          </Form.Item>

          <Form.Item name="prompt_template" label="Prompt Template">
            <Input.TextArea
              rows={4}
              placeholder="Optional prompt template for this stage..."
            />
          </Form.Item>

          <Form.Item
            name="auto_run"
            label="Auto Run"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
