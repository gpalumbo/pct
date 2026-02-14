import { useState } from 'react';
import { Button, Form, Input, Modal, Select, Space, Table, message } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useLoras, useCreateLora, useUpdateLora, useDeleteLora, useModels } from '../../hooks/useConfigQueries';
import type { LoRARegistryEntry } from '../../types/config';

export default function LoRARegistryTab() {
  const { data: loras = [], isLoading } = useLoras();
  const { data: models = [] } = useModels();
  const createLora = useCreateLora();
  const updateLora = useUpdateLora();
  const deleteLora = useDeleteLora();

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<LoRARegistryEntry | null>(null);
  const [form] = Form.useForm();

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setOpen(true);
  };

  const openEdit = (record: LoRARegistryEntry) => {
    setEditing(record);
    form.setFieldsValue(record);
    setOpen(true);
  };

  const handleOk = async () => {
    const values = await form.validateFields();
    if (editing) {
      await updateLora.mutateAsync({ id: editing.id, data: values });
      message.success('LoRA updated');
    } else {
      values.created = new Date().toISOString();
      await createLora.mutateAsync(values);
      message.success('LoRA created');
    }
    setOpen(false);
  };

  const handleDelete = async (id: string) => {
    await deleteLora.mutateAsync(id);
    message.success('LoRA deleted');
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id' },
    { title: 'Base Model', dataIndex: 'base_model', key: 'base_model' },
    { title: 'Path', dataIndex: 'path', key: 'path' },
    { title: 'Description', dataIndex: 'description', key: 'description' },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: unknown, record: LoRARegistryEntry) => (
        <Space>
          <Button icon={<EditOutlined />} size="small" onClick={() => openEdit(record)} />
          <Button icon={<DeleteOutlined />} size="small" danger onClick={() => handleDelete(record.id)} />
        </Space>
      ),
    },
  ];

  return (
    <>
      <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} style={{ marginBottom: 16 }}>
        Add LoRA
      </Button>
      <Table dataSource={loras} columns={columns} rowKey="id" loading={isLoading} size="small" />

      <Modal
        title={editing ? 'Edit LoRA' : 'Add LoRA'}
        open={open}
        onOk={handleOk}
        onCancel={() => setOpen(false)}
        confirmLoading={createLora.isPending || updateLora.isPending}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="id" label="ID" rules={[{ required: true }]}>
            <Input disabled={!!editing} />
          </Form.Item>
          <Form.Item name="base_model" label="Base Model" rules={[{ required: true }]}>
            <Select
              options={models.map((m) => ({ label: `${m.id} (${m.model_id})`, value: m.id }))}
              placeholder="Select base model"
            />
          </Form.Item>
          <Form.Item name="path" label="Path" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
