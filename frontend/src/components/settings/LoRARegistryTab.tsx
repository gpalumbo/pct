import { useState } from 'react';
import {
  Table,
  Typography,
  Button,
  Space,
  Modal,
  Form,
  Input,
  InputNumber,
  Popconfirm,
  Alert,
  Tag,
  Spin,
  App,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useLoras, useCreateLora, useUpdateLora, useDeleteLora, useAddLoraVersion } from '../../hooks/useConfigQueries';
import type { LoRARegistryEntry, LoRAVersion } from '../../types/config';

const { Title } = Typography;

export default function LoRARegistryTab() {
  const { message } = App.useApp();
  const { data: entries = [], isLoading } = useLoras();
  const createLora = useCreateLora();
  const updateLora = useUpdateLora();
  const deleteLora = useDeleteLora();
  const addVersion = useAddLoraVersion();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingEntry, setEditingEntry] = useState<LoRARegistryEntry | null>(null);
  const [versionModalOpen, setVersionModalOpen] = useState(false);
  const [versionTargetId, setVersionTargetId] = useState<string | null>(null);
  const [form] = Form.useForm();
  const [versionForm] = Form.useForm();

  // ── LoRA CRUD ──────────────────────────────────────────────

  const openAddModal = () => {
    setEditingEntry(null);
    form.resetFields();
    form.setFieldsValue({ active_version: 1 });
    setModalOpen(true);
  };

  const openEditModal = (entry: LoRARegistryEntry) => {
    setEditingEntry(entry);
    form.setFieldsValue({
      name: entry.name,
      base_model_id: entry.base_model_id,
      description: entry.description,
      active_version: entry.active_version,
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (editingEntry) {
        await updateLora.mutateAsync({
          id: editingEntry.id,
          data: values,
        });
        message.success('LoRA adapter updated');
      } else {
        await createLora.mutateAsync(values);
        message.success('LoRA adapter added');
      }
      setModalOpen(false);
      form.resetFields();
    } catch {
      // validation failed — modal stays open
    }
  };

  const handleDelete = async (id: string) => {
    await deleteLora.mutateAsync(id);
    message.success('LoRA adapter deleted');
  };

  // ── Version CRUD ───────────────────────────────────────────

  const openVersionModal = (loraId: string) => {
    setVersionTargetId(loraId);
    versionForm.resetFields();
    setVersionModalOpen(true);
  };

  const handleAddVersion = async () => {
    try {
      const values = await versionForm.validateFields();
      if (!versionTargetId) return;
      await addVersion.mutateAsync({
        loraId: versionTargetId,
        data: {
          file_path: values.file_path,
          training_job_id: values.training_job_id || null,
        },
      });
      message.success('Version added');
      setVersionModalOpen(false);
      versionForm.resetFields();
    } catch {
      // validation failed
    }
  };

  // ── Columns ────────────────────────────────────────────────

  const columns: ColumnsType<LoRARegistryEntry> = [
    { title: 'Name', dataIndex: 'name', key: 'name' },
    {
      title: 'Base Model ID',
      dataIndex: 'base_model_id',
      key: 'base_model_id',
      render: (val: string) => <Tag>{val}</Tag>,
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: 'Active Version',
      dataIndex: 'active_version',
      key: 'active_version',
      width: 130,
      align: 'center',
    },
    {
      title: 'Versions',
      key: 'versions',
      width: 100,
      align: 'center',
      render: (_: unknown, record: LoRARegistryEntry) => record.versions.length,
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: LoRARegistryEntry) => (
        <Space size="small">
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openEditModal(record)}
          />
          <Popconfirm
            title="Delete this LoRA adapter?"
            description="This action cannot be undone."
            onConfirm={() => handleDelete(record.id)}
            okText="Delete"
            cancelText="Cancel"
            okButtonProps={{ danger: true }}
          >
            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const versionColumns: ColumnsType<LoRAVersion> = [
    { title: 'Version', dataIndex: 'version', key: 'version', width: 90, align: 'center' },
    { title: 'File Path', dataIndex: 'file_path', key: 'file_path', ellipsis: true },
    {
      title: 'Training Job ID',
      dataIndex: 'training_job_id',
      key: 'training_job_id',
      render: (val: string | null) => val ?? <Typography.Text type="secondary">N/A</Typography.Text>,
    },
    { title: 'Created At', dataIndex: 'created_at', key: 'created_at', width: 200 },
  ];

  // ── Render ─────────────────────────────────────────────────

  if (isLoading) return <Spin size="large" style={{ display: 'block', margin: '60px auto' }} />;

  return (
    <div>
      <Alert
        message="LoRA adapter registry. Adapters can be assigned to agents for fine-tuned inference."
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Space style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Title level={5} style={{ margin: 0 }}>
          LoRA Registry
        </Title>
        <Button icon={<PlusOutlined />} type="primary" onClick={openAddModal}>
          Add LoRA
        </Button>
      </Space>

      <Table
        dataSource={entries}
        columns={columns}
        rowKey="id"
        locale={{ emptyText: 'No LoRA adapters registered yet' }}
        size="small"
        expandable={{
          expandedRowRender: (record) => (
            <div style={{ padding: '8px 0' }}>
              <Space style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
                <Typography.Text strong>Versions</Typography.Text>
                <Button
                  size="small"
                  icon={<PlusOutlined />}
                  onClick={() => openVersionModal(record.id)}
                >
                  Add Version
                </Button>
              </Space>
              <Table
                dataSource={record.versions}
                columns={versionColumns}
                rowKey="version"
                size="small"
                pagination={false}
                locale={{ emptyText: 'No versions yet' }}
              />
            </div>
          ),
        }}
      />

      {/* ── Add / Edit LoRA Modal ── */}
      <Modal
        title={editingEntry ? 'Edit LoRA Adapter' : 'Add LoRA Adapter'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => {
          setModalOpen(false);
          form.resetFields();
        }}
        okText={editingEntry ? 'Save' : 'Add'}
        confirmLoading={createLora.isPending || updateLora.isPending}
      >
        <Form form={form} layout="vertical" initialValues={{ active_version: 1 }}>
          <Form.Item
            name="name"
            label="Name"
            rules={[{ required: true, message: 'Name is required' }]}
          >
            <Input placeholder="e.g. my-lora-adapter" />
          </Form.Item>
          <Form.Item
            name="base_model_id"
            label="Base Model ID"
            rules={[{ required: true, message: 'Base Model ID is required' }]}
          >
            <Input placeholder="e.g. llama-3-8b" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={3} placeholder="Optional description of the adapter" />
          </Form.Item>
          <Form.Item name="active_version" label="Active Version">
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* ── Add Version Modal ── */}
      <Modal
        title="Add Version"
        open={versionModalOpen}
        onOk={handleAddVersion}
        onCancel={() => {
          setVersionModalOpen(false);
          versionForm.resetFields();
        }}
        okText="Add"
        confirmLoading={addVersion.isPending}
      >
        <Form form={versionForm} layout="vertical">
          <Form.Item
            name="file_path"
            label="File Path"
            rules={[{ required: true, message: 'File path is required' }]}
          >
            <Input placeholder="e.g. /models/loras/my-adapter-v2.gguf" />
          </Form.Item>
          <Form.Item name="training_job_id" label="Training Job ID">
            <Input placeholder="Optional training job reference" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
