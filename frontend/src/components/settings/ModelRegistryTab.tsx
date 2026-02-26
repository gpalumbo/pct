import { useState } from 'react';
import { Button, Form, Input, InputNumber, Modal, Select, Space, Table, message } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, FolderOpenOutlined } from '@ant-design/icons';
import {
  useModels,
  useCreateModel,
  useUpdateModel,
  useDeleteModel,
} from '../../hooks/useConfigQueries';
import type { ModelRegistryEntry, ProviderType } from '../../types/config';
import FileBrowser from './FileBrowser';

export default function ModelRegistryTab() {
  const { data: models = [], isLoading } = useModels();
  const createModel = useCreateModel();
  const updateModel = useUpdateModel();
  const deleteModel = useDeleteModel();

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<ModelRegistryEntry | null>(null);
  const [browseOpen, setBrowseOpen] = useState(false);
  const [form] = Form.useForm();

  const providerType = Form.useWatch('provider_type', form) as ProviderType | undefined;

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setOpen(true);
  };

  const openEdit = (record: ModelRegistryEntry) => {
    setEditing(record);
    form.setFieldsValue(record);
    setOpen(true);
  };

  const handleOk = async () => {
    const values = await form.validateFields();
    if (editing) {
      await updateModel.mutateAsync({ id: editing.id, data: values });
      message.success('Model updated');
    } else {
      await createModel.mutateAsync(values);
      message.success('Model created');
    }
    setOpen(false);
  };

  const handleDelete = async (id: string) => {
    await deleteModel.mutateAsync(id);
    message.success('Model deleted');
  };

  const handleFileSelect = (path: string) => {
    form.setFieldsValue({ model_path: path });
    setBrowseOpen(false);
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id' },
    { title: 'Provider', dataIndex: 'provider_type', key: 'provider_type' },
    { title: 'Model ID', dataIndex: 'model_id', key: 'model_id' },
    { title: 'Context Length', dataIndex: 'context_length', key: 'context_length' },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: unknown, record: ModelRegistryEntry) => (
        <Space>
          <Button icon={<EditOutlined />} size="small" onClick={() => openEdit(record)} />
          <Button
            icon={<DeleteOutlined />}
            size="small"
            danger
            onClick={() => handleDelete(record.id)}
          />
        </Space>
      ),
    },
  ];

  return (
    <>
      <Button
        type="primary"
        icon={<PlusOutlined />}
        onClick={openCreate}
        style={{ marginBottom: 16 }}
      >
        Add Model
      </Button>
      <Table dataSource={models} columns={columns} rowKey="id" loading={isLoading} size="small" />

      <Modal
        title={editing ? 'Edit Model' : 'Add Model'}
        open={open}
        onOk={handleOk}
        onCancel={() => setOpen(false)}
        confirmLoading={createModel.isPending || updateModel.isPending}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="id" label="ID" rules={[{ required: true }]}>
            <Input disabled={!!editing} />
          </Form.Item>
          <Form.Item name="provider_type" label="Provider Type" rules={[{ required: true }]}>
            <Select
              options={[
                { label: 'Remote API', value: 'remote' },
                { label: 'Local LLM', value: 'local' },
                { label: 'HuggingFace', value: 'huggingface' },
              ]}
            />
          </Form.Item>
          <Form.Item name="model_id" label="Model ID" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="context_length"
            label="Context Length"
            initialValue={0}
            rules={[{ required: true }]}
            tooltip="0 = use model's training context length"
          >
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          {(providerType === 'local' || providerType === 'huggingface') && (
            <Form.Item label="Model Path" required style={{ marginBottom: 0 }}>
              <div style={{ display: 'flex', gap: 8 }}>
                <Form.Item
                  name="model_path"
                  noStyle
                  rules={[{ required: true, message: 'Model path is required for local models' }]}
                >
                  <Input style={{ flex: 1 }} />
                </Form.Item>
                <Button icon={<FolderOpenOutlined />} onClick={() => setBrowseOpen(true)} />
              </div>
            </Form.Item>
          )}
          {providerType === 'remote' && (
            <Form.Item name="api_base" label="API Base URL">
              <Input />
            </Form.Item>
          )}
        </Form>
      </Modal>

      <FileBrowser
        open={browseOpen}
        onCancel={() => setBrowseOpen(false)}
        onSelect={handleFileSelect}
        title="Select Model File"
      />
    </>
  );
}
