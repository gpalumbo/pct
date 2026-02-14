import { useState } from 'react';
import { Button, Form, Input, InputNumber, Modal, Select, Space, Table, message } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import {
  useAgents, useCreateAgent, useUpdateAgent, useDeleteAgent,
  useModels, useLoras,
} from '../../hooks/useConfigQueries';
import type { AgentConfig, ProviderType } from '../../types/config';

export default function AgentsTab() {
  const { data: agents = [], isLoading } = useAgents();
  const { data: models = [] } = useModels();
  const { data: loras = [] } = useLoras();
  const createAgent = useCreateAgent();
  const updateAgent = useUpdateAgent();
  const deleteAgent = useDeleteAgent();

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<AgentConfig | null>(null);
  const [form] = Form.useForm();

  const selectedModel = Form.useWatch('model', form) as string | undefined;
  const providerType = Form.useWatch('provider_type', form) as ProviderType | undefined;

  const filteredLoras = loras.filter((l) => l.base_model === selectedModel);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setOpen(true);
  };

  const openEdit = (record: AgentConfig) => {
    setEditing(record);
    form.setFieldsValue(record);
    setOpen(true);
  };

  const handleOk = async () => {
    const values = await form.validateFields();
    if (editing) {
      await updateAgent.mutateAsync({ id: editing.id, data: values });
      message.success('Agent updated');
    } else {
      await createAgent.mutateAsync(values);
      message.success('Agent created');
    }
    setOpen(false);
  };

  const handleDelete = async (id: string) => {
    await deleteAgent.mutateAsync(id);
    message.success('Agent deleted');
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id' },
    { title: 'Type', dataIndex: 'agent_type', key: 'agent_type' },
    { title: 'Provider', dataIndex: 'provider_type', key: 'provider_type' },
    { title: 'Model', dataIndex: 'model', key: 'model' },
    { title: 'LoRA', dataIndex: 'lora', key: 'lora' },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: unknown, record: AgentConfig) => (
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
        Add Agent
      </Button>
      <Table dataSource={agents} columns={columns} rowKey="id" loading={isLoading} size="small" />

      <Modal
        title={editing ? 'Edit Agent' : 'Add Agent'}
        open={open}
        onOk={handleOk}
        onCancel={() => setOpen(false)}
        confirmLoading={createAgent.isPending || updateAgent.isPending}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="id" label="ID" rules={[{ required: true }]}>
            <Input disabled={!!editing} />
          </Form.Item>
          <Form.Item name="agent_type" label="Agent Type" rules={[{ required: true }]}>
            <Select options={[
              { label: 'LLM', value: 'llm' },
              { label: 'User', value: 'user' },
              { label: 'Tool', value: 'tool' },
            ]} />
          </Form.Item>
          <Form.Item name="provider_type" label="Provider Type" rules={[{ required: true }]}>
            <Select options={[
              { label: 'Remote API', value: 'remote' },
              { label: 'Local LLM', value: 'local' },
              { label: 'User', value: 'user' },
            ]} />
          </Form.Item>
          <Form.Item name="model" label="Model" rules={[{ required: true }]}>
            <Select
              options={models.map((m) => ({ label: `${m.id} (${m.model_id})`, value: m.id }))}
              placeholder="Select model from registry"
            />
          </Form.Item>
          <Form.Item name="lora" label="LoRA">
            <Select
              allowClear
              options={filteredLoras.map((l) => ({ label: `${l.id} — ${l.description || l.path}`, value: l.id }))}
              placeholder={selectedModel ? 'Select LoRA (filtered by model)' : 'Select a model first'}
              disabled={!selectedModel}
            />
          </Form.Item>
          <Form.Item name="prompt_template" label="Prompt Template">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="context_length" label="Context Length Override">
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          {providerType !== 'user' && (
            <Form.Item name="temperature" label="Temperature">
              <InputNumber min={0} max={2} step={0.1} style={{ width: '100%' }} placeholder="Model default" />
            </Form.Item>
          )}
          {providerType === 'remote' && (
            <Form.Item name="cli_command" label="CLI Command">
              <Input />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </>
  );
}
