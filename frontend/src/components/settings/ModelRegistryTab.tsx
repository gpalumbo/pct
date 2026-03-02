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
  InputNumber,
  Select,
  Popconfirm,
  Alert,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ModelRegistryEntry } from '../../types/config';
import type { ProviderType, DownloadStatus } from '../../types/enums';

const { Title } = Typography;

const providerTypeOptions: { label: string; value: ProviderType }[] = [
  { label: 'Remote API', value: 'remote_api' },
  { label: 'Local', value: 'local' },
  { label: 'HuggingFace', value: 'huggingface' },
  { label: 'User', value: 'user' },
];

const downloadStatusOptions: { label: string; value: DownloadStatus }[] = [
  { label: 'Pending', value: 'pending' },
  { label: 'Downloading', value: 'downloading' },
  { label: 'Ready', value: 'ready' },
  { label: 'Error', value: 'error' },
];

const providerTagColor: Record<ProviderType, string> = {
  remote_api: 'blue',
  local: 'green',
  huggingface: 'orange',
  user: 'purple',
};

const statusTagColor: Record<DownloadStatus, string> = {
  pending: 'default',
  downloading: 'processing',
  ready: 'success',
  error: 'error',
};

interface ModelFormValues {
  name: string;
  provider_type: ProviderType;
  model_identifier: string;
  context_length: number;
  api_base_url?: string;
  file_path?: string;
  download_status?: DownloadStatus;
}

export default function ModelRegistryTab() {
  const [models, setModels] = useState<ModelRegistryEntry[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<ModelRegistryEntry | null>(null);
  const [form] = Form.useForm<ModelFormValues>();

  const openAddModal = () => {
    setEditingModel(null);
    form.resetFields();
    form.setFieldsValue({ context_length: 4096 });
    setModalOpen(true);
  };

  const openEditModal = (record: ModelRegistryEntry) => {
    setEditingModel(record);
    form.setFieldsValue({
      name: record.name,
      provider_type: record.provider_type as ProviderType,
      model_identifier: record.model_identifier,
      context_length: record.context_length,
      api_base_url: record.api_base_url ?? undefined,
      file_path: record.file_path ?? undefined,
      download_status: (record.download_status as DownloadStatus) ?? undefined,
    });
    setModalOpen(true);
  };

  const handleDelete = (id: string) => {
    setModels((prev) => prev.filter((m) => m.id !== id));
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingModel) {
        // Update existing
        setModels((prev) =>
          prev.map((m) =>
            m.id === editingModel.id
              ? {
                  ...m,
                  ...values,
                  api_base_url: values.api_base_url || null,
                  file_path: values.file_path || null,
                  download_status: values.download_status || null,
                }
              : m,
          ),
        );
      } else {
        // Create new
        const newEntry: ModelRegistryEntry = {
          id: crypto.randomUUID(),
          name: values.name,
          provider_type: values.provider_type,
          model_identifier: values.model_identifier,
          context_length: values.context_length,
          api_base_url: values.api_base_url || null,
          file_path: values.file_path || null,
          download_status: values.download_status || null,
        };
        setModels((prev) => [...prev, newEntry]);
      }
      setModalOpen(false);
      form.resetFields();
      setEditingModel(null);
    } catch {
      // validation failed — form will show inline errors
    }
  };

  const handleCancel = () => {
    setModalOpen(false);
    form.resetFields();
    setEditingModel(null);
  };

  const columns = [
    { title: 'Name', dataIndex: 'name', key: 'name' },
    {
      title: 'Provider',
      dataIndex: 'provider_type',
      key: 'provider_type',
      render: (type: ProviderType) => (
        <Tag color={providerTagColor[type] ?? 'default'}>{type}</Tag>
      ),
    },
    { title: 'Model ID', dataIndex: 'model_identifier', key: 'model_identifier' },
    {
      title: 'Context Length',
      dataIndex: 'context_length',
      key: 'context_length',
      render: (v: number) => v.toLocaleString(),
    },
    {
      title: 'Status',
      dataIndex: 'download_status',
      key: 'download_status',
      render: (status: DownloadStatus | null) =>
        status ? <Tag color={statusTagColor[status] ?? 'default'}>{status}</Tag> : 'N/A',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: unknown, record: ModelRegistryEntry) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openEditModal(record)}
          >
            Edit
          </Button>
          <Popconfirm
            title="Delete model"
            description={`Remove "${record.name}" from the registry?`}
            onConfirm={() => handleDelete(record.id)}
            okText="Delete"
            okButtonProps={{ danger: true }}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Alert
        type="info"
        showIcon
        message="Model registry entries are auto-discovered from your models directory. You can also manually add entries here."
        style={{ marginBottom: 16 }}
      />
      <Alert
        type="warning"
        showIcon
        message="Note: Model registry persistence coming soon. Entries added here are stored in browser memory only."
        style={{ marginBottom: 16 }}
      />

      <Space style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Title level={5} style={{ margin: 0 }}>
          Model Registry
        </Title>
        <Button icon={<PlusOutlined />} type="primary" onClick={openAddModal}>
          Add Model
        </Button>
      </Space>

      <Table
        dataSource={models}
        columns={columns}
        rowKey="id"
        locale={{ emptyText: 'No models registered yet. Click "Add Model" to get started.' }}
        size="small"
      />

      <Modal
        title={editingModel ? 'Edit Model' : 'Add Model'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={handleCancel}
        okText={editingModel ? 'Save' : 'Add'}
        width={560}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ context_length: 4096 }}
        >
          <Form.Item
            name="name"
            label="Name"
            rules={[{ required: true, message: 'Please enter a model name' }]}
          >
            <Input placeholder="e.g. GPT-4o, Llama 3.1 8B" />
          </Form.Item>

          <Form.Item
            name="provider_type"
            label="Provider Type"
            rules={[{ required: true, message: 'Please select a provider type' }]}
          >
            <Select options={providerTypeOptions} placeholder="Select provider type" />
          </Form.Item>

          <Form.Item
            name="model_identifier"
            label="Model Identifier"
            rules={[{ required: true, message: 'Please enter a model identifier' }]}
          >
            <Input placeholder="e.g. gpt-4o, meta-llama/Llama-3.1-8B" />
          </Form.Item>

          <Form.Item
            name="context_length"
            label="Context Length"
            rules={[{ required: true, message: 'Please enter the context length' }]}
          >
            <InputNumber
              min={0}
              max={2_000_000}
              step={1024}
              style={{ width: '100%' }}
              placeholder="e.g. 4096"
            />
          </Form.Item>

          <Form.Item
            name="api_base_url"
            label="API Base URL"
            tooltip="Required for remote_api providers. The base URL for the model API."
          >
            <Input placeholder="e.g. https://api.openai.com/v1" />
          </Form.Item>

          <Form.Item
            name="file_path"
            label="File Path"
            tooltip="Required for local providers. Path to the model file on disk."
          >
            <Input placeholder="e.g. /models/llama-3.1-8b.gguf" />
          </Form.Item>

          <Form.Item
            name="download_status"
            label="Download Status"
            tooltip="Current download status for models that need to be fetched."
          >
            <Select
              options={downloadStatusOptions}
              placeholder="Select status (optional)"
              allowClear
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
