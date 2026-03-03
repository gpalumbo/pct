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
  App,
  List,
  Breadcrumb,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, FolderOpenOutlined, FolderOutlined, FileOutlined } from '@ant-design/icons';
import { useModels, useCreateModel, useUpdateModel, useDeleteModel, useProject } from '../../hooks/useConfigQueries';
import { configApi } from '../../api/configApi';
import type { ModelRegistryEntry, FileEntry } from '../../types/config';
import type { ProviderType, DownloadStatus } from '../../types/enums';

const { Title } = Typography;

const providerTypeOptions: { label: string; value: ProviderType }[] = [
  { label: 'Remote API', value: 'remote_api' },
  { label: 'Local', value: 'local' },
  { label: 'HuggingFace', value: 'huggingface' },
  { label: 'User', value: 'user' },
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
}

export default function ModelRegistryTab() {
  const { message } = App.useApp();
  const { data: models, isLoading } = useModels();
  const { data: project } = useProject();
  const createModel = useCreateModel();
  const updateModel = useUpdateModel();
  const deleteModel = useDeleteModel();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<ModelRegistryEntry | null>(null);
  const [form] = Form.useForm<ModelFormValues>();

  // File browser state
  const [browseOpen, setBrowseOpen] = useState(false);
  const [browseEntries, setBrowseEntries] = useState<FileEntry[]>([]);
  const [browsePath, setBrowsePath] = useState('');
  const [browseLoading, setBrowseLoading] = useState(false);

  const loadBrowseDir = async (path: string) => {
    setBrowseLoading(true);
    try {
      const entries = await configApi.browseFiles(path);
      setBrowseEntries(entries);
      setBrowsePath(path);
    } catch {
      message.error('Failed to browse directory');
    } finally {
      setBrowseLoading(false);
    }
  };

  const openFileBrowser = () => {
    setBrowseOpen(true);
    loadBrowseDir('');
  };

  const selectFile = (entry: FileEntry) => {
    if (entry.is_dir) {
      loadBrowseDir(entry.path);
    } else {
      const projectDir = project?.directory ?? '';
      const fullPath = projectDir ? `${projectDir}/${entry.path}`.replace(/\\/g, '/') : entry.path;
      form.setFieldsValue({ file_path: fullPath });
      setBrowseOpen(false);
    }
  };

  // Auto-default file_path for HuggingFace models when model_identifier changes
  const handleProviderOrIdChange = () => {
    const providerType = form.getFieldValue('provider_type');
    const modelId = form.getFieldValue('model_identifier');
    if (providerType === 'huggingface' && modelId) {
      const projectDir = project?.directory ?? '';
      const safeName = modelId.replace(/\//g, '-');
      const defaultPath = projectDir
        ? `${projectDir}/models/${safeName}`.replace(/\\/g, '/')
        : `models/${safeName}`;
      form.setFieldsValue({ file_path: defaultPath });
    }
  };

  const openAddModal = () => {
    setEditingModel(null);
    form.resetFields();
    form.setFieldsValue({ context_length: 0 });
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
    });
    setModalOpen(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteModel.mutateAsync(id);
      message.success('Model deleted');
    } catch {
      message.error('Failed to delete model');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const payload = {
        ...values,
        api_base_url: values.api_base_url || null,
        file_path: values.file_path || null,
      };

      if (editingModel) {
        await updateModel.mutateAsync({ id: editingModel.id, data: payload });
        message.success('Model updated');
      } else {
        await createModel.mutateAsync(payload);
        message.success('Model added');
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

      <Space style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Title level={5} style={{ margin: 0 }}>
          Model Registry
        </Title>
        <Button icon={<PlusOutlined />} type="primary" onClick={openAddModal}>
          Add Model
        </Button>
      </Space>

      <Table
        dataSource={models ?? []}
        columns={columns}
        rowKey="id"
        loading={isLoading}
        locale={{ emptyText: 'No models registered yet. Click "Add Model" to get started.' }}
        size="small"
      />

      <Modal
        title={editingModel ? 'Edit Model' : 'Add Model'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={handleCancel}
        okText={editingModel ? 'Save' : 'Add'}
        confirmLoading={createModel.isPending || updateModel.isPending}
        width={560}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ context_length: 0 }}
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
            <Select
              options={providerTypeOptions}
              placeholder="Select provider type"
              onChange={handleProviderOrIdChange}
            />
          </Form.Item>

          <Form.Item
            name="model_identifier"
            label="Model Identifier"
            rules={[{ required: true, message: 'Please enter a model identifier' }]}
          >
            <Input
              placeholder="e.g. gpt-4o, meta-llama/Llama-3.1-8B"
              onBlur={handleProviderOrIdChange}
            />
          </Form.Item>

          <Form.Item
            name="context_length"
            label="Context Length"
          >
            <InputNumber
              min={0}
              max={2_000_000}
              step={1024}
              style={{ width: '100%' }}
              placeholder="0"
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
            tooltip="Path to the model file on disk. For HuggingFace models, auto-populated from model ID."
          >
            <Input
              placeholder="e.g. /models/llama-3.1-8b.gguf"
              addonAfter={
                <FolderOpenOutlined
                  onClick={openFileBrowser}
                  style={{ cursor: 'pointer' }}
                  title="Browse files"
                />
              }
            />
          </Form.Item>

          {editingModel?.download_status && (
            <Form.Item label="Download Status">
              <Tag color={statusTagColor[editingModel.download_status as DownloadStatus] ?? 'default'}>
                {editingModel.download_status}
              </Tag>
            </Form.Item>
          )}
        </Form>
      </Modal>

      {/* File Browser Modal */}
      <Modal
        title="Browse Files"
        open={browseOpen}
        onCancel={() => setBrowseOpen(false)}
        footer={null}
        width={560}
      >
        <Breadcrumb
          style={{ marginBottom: 12 }}
          items={[
            {
              title: <a onClick={() => loadBrowseDir('')}>Project Root</a>,
            },
            ...browsePath.split('/').filter(Boolean).map((seg, i, arr) => ({
              title: (
                <a onClick={() => loadBrowseDir(arr.slice(0, i + 1).join('/'))}>
                  {seg}
                </a>
              ),
            })),
          ]}
        />
        <List
          loading={browseLoading}
          dataSource={browseEntries}
          size="small"
          style={{ maxHeight: 400, overflow: 'auto' }}
          locale={{ emptyText: 'Empty directory' }}
          renderItem={(entry) => (
            <List.Item
              onClick={() => selectFile(entry)}
              style={{ cursor: 'pointer', padding: '6px 12px' }}
            >
              <Space>
                {entry.is_dir ? <FolderOutlined style={{ color: '#faad14' }} /> : <FileOutlined />}
                <span>{entry.name}</span>
              </Space>
              {!entry.is_dir && (
                <span style={{ color: '#999', fontSize: 12 }}>
                  {(entry.size / 1024).toFixed(1)} KB
                </span>
              )}
            </List.Item>
          )}
        />
      </Modal>
    </div>
  );
}
