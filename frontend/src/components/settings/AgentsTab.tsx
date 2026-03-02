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
  Switch,
  Popconfirm,
  message,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useProject, useUpdateProject } from '../../hooks/useConfigQueries';
import type { Agent, Project } from '../../types/config';
import type { AgentType } from '../../types/enums';

const { Title } = Typography;

const AGENT_TYPE_OPTIONS: { label: string; value: AgentType }[] = [
  { label: 'LLM', value: 'llm' },
  { label: 'User', value: 'user' },
  { label: 'Tool', value: 'tool' },
  { label: 'Image Gen', value: 'image_gen' },
];

const AGENT_TYPE_COLORS: Record<AgentType, string> = {
  llm: 'blue',
  user: 'green',
  tool: 'orange',
  image_gen: 'purple',
};

interface AgentFormValues {
  name: string;
  agent_type: AgentType;
  model_id: string;
  lora_id?: string;
  prompt_template?: string;
  temperature?: number;
  context_length_override?: number;
  cli_command?: string;
  linked_user_id?: string;
  notify_on_waiting: boolean;
}

export default function AgentsTab() {
  const { data: project } = useProject();
  const updateProject = useUpdateProject();
  const agents: Agent[] = project?.agents ?? [];

  const [modalOpen, setModalOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [form] = Form.useForm<AgentFormValues>();

  const openAddModal = () => {
    setEditingAgent(null);
    form.resetFields();
    form.setFieldsValue({ notify_on_waiting: false });
    setModalOpen(true);
  };

  const openEditModal = (agent: Agent) => {
    setEditingAgent(agent);
    form.setFieldsValue({
      name: agent.name,
      agent_type: agent.agent_type as AgentType,
      model_id: agent.model_id,
      lora_id: agent.lora_id ?? undefined,
      prompt_template: agent.prompt_template ?? undefined,
      temperature: agent.temperature ?? undefined,
      context_length_override: agent.context_length_override ?? undefined,
      cli_command: agent.cli_command ?? undefined,
      linked_user_id: agent.linked_user_id ?? undefined,
      notify_on_waiting: agent.notify_on_waiting,
    });
    setModalOpen(true);
  };

  const handleCancel = () => {
    setModalOpen(false);
    setEditingAgent(null);
    form.resetFields();
  };

  const saveAgents = (updatedAgents: Agent[]) => {
    if (!project) return;
    const updated: Project = { ...project, agents: updatedAgents };
    updateProject.mutate(updated, {
      onSuccess: () => message.success('Agents updated'),
      onError: () => message.error('Failed to update agents'),
    });
  };

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      const agentData: Agent = {
        id: editingAgent?.id ?? crypto.randomUUID(),
        name: values.name,
        agent_type: values.agent_type,
        model_id: values.model_id,
        lora_id: values.lora_id || null,
        prompt_template: values.prompt_template || null,
        temperature: values.temperature ?? null,
        context_length_override: values.context_length_override ?? null,
        cli_command: values.cli_command || null,
        linked_user_id: values.linked_user_id || null,
        notify_on_waiting: values.notify_on_waiting ?? false,
      };

      let updatedAgents: Agent[];
      if (editingAgent) {
        updatedAgents = agents.map((a) => (a.id === editingAgent.id ? agentData : a));
      } else {
        updatedAgents = [...agents, agentData];
      }

      saveAgents(updatedAgents);
      setModalOpen(false);
      setEditingAgent(null);
      form.resetFields();
    } catch {
      // validation failed — form will show inline errors
    }
  };

  const handleDelete = (agentId: string) => {
    const updatedAgents = agents.filter((a) => a.id !== agentId);
    saveAgents(updatedAgents);
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Agent Type',
      dataIndex: 'agent_type',
      key: 'agent_type',
      render: (type: AgentType) => (
        <Tag color={AGENT_TYPE_COLORS[type] ?? 'default'}>{type}</Tag>
      ),
    },
    {
      title: 'Model ID',
      dataIndex: 'model_id',
      key: 'model_id',
      ellipsis: true,
    },
    {
      title: 'LoRA ID',
      dataIndex: 'lora_id',
      key: 'lora_id',
      render: (v: string | null) => v ?? '--',
    },
    {
      title: 'Temperature',
      dataIndex: 'temperature',
      key: 'temperature',
      width: 110,
      render: (v: number | null) => (v != null ? v.toFixed(1) : '--'),
    },
    {
      title: 'Context Length',
      dataIndex: 'context_length_override',
      key: 'context_length_override',
      width: 130,
      render: (v: number | null) => (v != null ? v.toLocaleString() : '--'),
    },
    {
      title: 'CLI Command',
      dataIndex: 'cli_command',
      key: 'cli_command',
      ellipsis: true,
      render: (v: string | null) => v ?? '--',
    },
    {
      title: 'Notify on Waiting',
      dataIndex: 'notify_on_waiting',
      key: 'notify_on_waiting',
      width: 140,
      render: (checked: boolean, record: Agent) => (
        <Switch
          size="small"
          checked={checked}
          onChange={(val) => {
            const updatedAgents = agents.map((a) =>
              a.id === record.id ? { ...a, notify_on_waiting: val } : a,
            );
            saveAgents(updatedAgents);
          }}
        />
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: Agent) => (
        <Space size="small">
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openEditModal(record)}
          />
          <Popconfirm
            title="Delete agent"
            description={`Remove "${record.name}"?`}
            onConfirm={() => handleDelete(record.id)}
            okText="Delete"
            okType="danger"
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
          Agents
        </Title>
        <Button icon={<PlusOutlined />} type="primary" onClick={openAddModal}>
          Add Agent
        </Button>
      </Space>

      <Table
        dataSource={agents}
        columns={columns}
        rowKey="id"
        locale={{ emptyText: 'No agents configured yet' }}
        size="small"
        scroll={{ x: 900 }}
      />

      <Modal
        title={editingAgent ? 'Edit Agent' : 'Add Agent'}
        open={modalOpen}
        onOk={handleOk}
        onCancel={handleCancel}
        confirmLoading={updateProject.isPending}
        okText={editingAgent ? 'Save' : 'Add'}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ notify_on_waiting: false }}
        >
          <Form.Item
            name="name"
            label="Name"
            rules={[{ required: true, message: 'Agent name is required' }]}
          >
            <Input placeholder="e.g. Primary LLM" />
          </Form.Item>

          <Form.Item
            name="agent_type"
            label="Agent Type"
            rules={[{ required: true, message: 'Agent type is required' }]}
          >
            <Select placeholder="Select agent type" options={AGENT_TYPE_OPTIONS} />
          </Form.Item>

          <Form.Item
            name="model_id"
            label="Model ID"
            rules={[{ required: true, message: 'Model ID is required' }]}
          >
            <Input placeholder="e.g. gpt-4o or local-llama-3" />
          </Form.Item>

          <Form.Item name="lora_id" label="LoRA ID">
            <Input placeholder="Optional LoRA adapter ID" />
          </Form.Item>

          <Form.Item name="prompt_template" label="Prompt Template">
            <Input.TextArea rows={3} placeholder="Optional system prompt template" />
          </Form.Item>

          <Form.Item name="temperature" label="Temperature">
            <InputNumber min={0} max={2} step={0.1} placeholder="0.0 - 2.0" style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="context_length_override" label="Context Length Override">
            <InputNumber min={1} step={1} placeholder="Override model default" style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="cli_command" label="CLI Command">
            <Input placeholder="Command for tool-type agents" />
          </Form.Item>

          <Form.Item name="linked_user_id" label="Linked User ID">
            <Input placeholder="Optional user ID to link" />
          </Form.Item>

          <Form.Item name="notify_on_waiting" label="Notify on Waiting" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
