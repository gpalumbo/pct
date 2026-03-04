import { useState } from 'react';
import {
  Table,
  Typography,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Popconfirm,
  ColorPicker,
  App,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useProject, useUpdateProject } from '../../hooks/useConfigQueries';
import type { ArtifactType } from '../../types/config';
import { toSlug } from '../../utils/slug';

const { Title } = Typography;

interface FormValues {
  label: string;
  color?: string | null;
  template_hint?: string | null;
}

export default function ArtifactTypesTab() {
  const { message } = App.useApp();
  const { data: project } = useProject();
  const updateProject = useUpdateProject();
  const types: ArtifactType[] = project?.artifact_types ?? [];

  const [modalOpen, setModalOpen] = useState(false);
  const [editingType, setEditingType] = useState<ArtifactType | null>(null);
  const [form] = Form.useForm<FormValues>();

  const openAdd = () => {
    setEditingType(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (record: ArtifactType) => {
    setEditingType(record);
    form.setFieldsValue({
      label: record.label,
      color: record.color ?? undefined,
      template_hint: record.template_hint ?? undefined,
    });
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditingType(null);
    form.resetFields();
  };

  const handleSave = async () => {
    if (!project) return;
    try {
      const values = await form.validateFields();
      let updated: ArtifactType[];

      if (editingType) {
        // Edit existing
        updated = types.map((t) =>
          t.id === editingType.id
            ? {
                ...t,
                label: values.label,
                color: values.color || null,
                template_hint: values.template_hint || null,
              }
            : t,
        );
      } else {
        // Add new
        const id = toSlug(values.label);
        if (types.some((t) => t.id === id)) {
          message.error(`Artifact type "${id}" already exists`);
          return;
        }
        const newType: ArtifactType = {
          id,
          label: values.label,
          color: values.color || null,
          template_hint: values.template_hint || null,
        };
        updated = [...types, newType];
      }

      await updateProject.mutateAsync({
        ...project,
        artifact_types: updated,
      });

      message.success(editingType ? 'Artifact type updated' : 'Artifact type added');
      closeModal();
    } catch {
      // validation error — form will show inline messages
    }
  };

  const handleDelete = async (id: string) => {
    if (!project) return;
    const updated = types.filter((t) => t.id !== id);
    await updateProject.mutateAsync({
      ...project,
      artifact_types: updated,
    });
    message.success('Artifact type deleted');
  };

  const columns = [
    { title: 'Label', dataIndex: 'label', key: 'label' },
    {
      title: 'Color',
      dataIndex: 'color',
      key: 'color',
      render: (color: string | null | undefined) =>
        color ? (
          <Space size={8}>
            <span
              style={{
                display: 'inline-block',
                width: 14,
                height: 14,
                borderRadius: '50%',
                backgroundColor: color,
                border: '1px solid var(--pct-color-border)',
                verticalAlign: 'middle',
              }}
            />
            <Tag color={color}>{color}</Tag>
          </Space>
        ) : (
          <span style={{ color: 'var(--pct-color-text-muted)' }}>Default</span>
        ),
    },
    {
      title: 'Template Hint',
      dataIndex: 'template_hint',
      key: 'template_hint',
      render: (hint: string | null | undefined) =>
        hint ? (
          <span style={{ maxWidth: 300, display: 'inline-block' }}>{hint}</span>
        ) : (
          <span style={{ color: 'var(--pct-color-text-muted)' }}>--</span>
        ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: ArtifactType) => (
        <Space size="small">
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openEdit(record)}
          />
          <Popconfirm
            title="Delete artifact type"
            description={`Remove "${record.label}"?`}
            onConfirm={() => handleDelete(record.id)}
            okText="Delete"
            okButtonProps={{ danger: true }}
          >
            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Title level={5} style={{ margin: 0 }}>
          Artifact Types
        </Title>
        <Button icon={<PlusOutlined />} type="primary" onClick={openAdd}>
          Add Artifact Type
        </Button>
      </Space>
      <Table
        dataSource={types}
        columns={columns}
        rowKey="id"
        pagination={false}
        locale={{ emptyText: 'No artifact types defined yet' }}
        size="small"
      />

      <Modal
        title={editingType ? 'Edit Artifact Type' : 'Add Artifact Type'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={closeModal}
        confirmLoading={updateProject.isPending}
        okText={editingType ? 'Save' : 'Add'}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="label"
            label="Label"
            rules={[{ required: true, message: 'Label is required' }]}
          >
            <Input placeholder="e.g. Design Document" />
          </Form.Item>

          <Form.Item name="color" label="Color">
            <ColorInput />
          </Form.Item>

          <Form.Item name="template_hint" label="Template Hint">
            <Input.TextArea
              rows={3}
              placeholder="Hint text describing what content should go in this artifact type"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

/**
 * Custom color input that combines a text input with Ant Design's ColorPicker.
 * Accepts and emits hex color strings for Form compatibility.
 */
function ColorInput({
  value,
  onChange,
}: {
  value?: string;
  onChange?: (value: string | undefined) => void;
}) {
  const handleColorPick = (_: unknown, hex: string) => {
    onChange?.(hex);
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    onChange?.(v || undefined);
  };

  return (
    <Space>
      <ColorPicker
        value={value || '#1677ff'}
        onChange={handleColorPick}
        size="middle"
      />
      <Input
        value={value ?? ''}
        onChange={handleTextChange}
        placeholder="#1677ff"
        style={{ width: 140 }}
        allowClear
      />
    </Space>
  );
}
