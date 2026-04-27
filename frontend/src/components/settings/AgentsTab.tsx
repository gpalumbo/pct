import { useState, useMemo } from 'react';
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
  Tabs,
  Checkbox,
  message,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useProject, useUpdateProject, useModels, useLoras } from '../../hooks/useConfigQueries';
import { useImagegenModels } from '../../hooks/useImageGenQueries';
import type { Agent, Project } from '../../types/config';
import type { AgentType } from '../../types/enums';
import { toSlug } from '../../utils/slug';

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
  id: string;
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
  // Image-gen
  num_inference_steps?: number;
  guidance_scale?: number;
  negative_prompt?: string;
  num_images?: number;
  default_draft?: boolean;
  max_sequence_length?: number;
  true_cfg_scale?: number;
}

// ── Shared image-gen form fields ──────────────────────────────────

function CommonImageGenFields() {
  return (
    <>
      <Form.Item
        name="num_inference_steps"
        label="Inference Steps"
        tooltip="Number of denoising steps. SD1.5: ~25, SDXL: ~30, Flux-dev: ~28, Flux-schnell: ~4"
      >
        <InputNumber placeholder="Model default" style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item
        name="guidance_scale"
        label="Guidance Scale"
        tooltip="CFG scale. SD1.5/SDXL: 5–15 (default 7.5). Flux: 1–5 (default 3.5, acts as embedded guidance)"
      >
        <InputNumber step={0.5} placeholder="Model default" style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item
        name="negative_prompt"
        label="Default Negative Prompt"
        tooltip="Applied to every generation unless overridden. Common: 'blurry, low quality, watermark, deformed'"
      >
        <Input.TextArea rows={2} placeholder="e.g. blurry, low quality, watermark" />
      </Form.Item>

      <Form.Item
        name="num_images"
        label="Images per Round"
        tooltip="How many images to generate per request. Typical: 1–6 (default 4)"
      >
        <InputNumber placeholder="4" style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item name="default_draft" valuePropName="checked">
        <Checkbox>Default to draft mode (half resolution, fewer steps)</Checkbox>
      </Form.Item>
    </>
  );
}

function FluxFields() {
  return (
    <>
      <Form.Item
        name="max_sequence_length"
        label="Max Sequence Length"
        tooltip="T5 text encoder max tokens. 512 for complex prompts, 256 for speed/VRAM savings"
      >
        <InputNumber placeholder="512" style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item
        name="true_cfg_scale"
        label="True CFG Scale"
        tooltip="Enables real classifier-free guidance on top of Flux's embedded guidance. 1.0 = off, 2–4 typical. Doubles inference time."
      >
        <InputNumber step={0.5} placeholder="Off" style={{ width: '100%' }} />
      </Form.Item>
    </>
  );
}

type ImagegenModelInfo = { id: string; architecture?: string };

const ARCH_LABELS: Record<string, string> = {
  sdxl: 'SDXL',
  sd15: 'SD 1.5',
  sd3: 'SD 3',
  flux: 'Flux',
  qwen: 'Qwen-Image',
  pixart: 'PixArt',
  kandinsky: 'Kandinsky',
  wuerstchen: 'Würstchen',
};

const ARCH_TAG_COLORS: Record<string, string> = {
  sdxl: 'blue',
  sd15: 'cyan',
  sd3: 'geekblue',
  flux: 'purple',
  qwen: 'gold',
  pixart: 'magenta',
  kandinsky: 'volcano',
  wuerstchen: 'orange',
};

function ImageGenFields({
  modelId,
  imagegenModels,
  modelDownloadStatus,
}: {
  modelId?: string;
  imagegenModels?: ImagegenModelInfo[];
  modelDownloadStatus?: string | null;
}) {
  const inImagegenList = !!imagegenModels?.some((m) => m.id === modelId);
  const arch = imagegenModels?.find((m) => m.id === modelId)?.architecture;
  const isFlux = arch === 'flux';
  const isSdFamily = arch === 'sdxl' || arch === 'sd15' || arch === 'sd3' || arch === 'qwen';
  const archKnown = isFlux || isSdFamily;

  // Status badge: detected | pending download | unknown
  let statusBadge: { color: string; text: string };
  if (arch && ARCH_LABELS[arch]) {
    statusBadge = {
      color: ARCH_TAG_COLORS[arch] ?? 'green',
      text: `Detected: ${ARCH_LABELS[arch]}`,
    };
  } else if (!inImagegenList || modelDownloadStatus !== 'ready') {
    statusBadge = {
      color: 'orange',
      text: 'Architecture pending — download model to detect',
    };
  } else {
    statusBadge = {
      color: 'red',
      text: 'Unknown architecture',
    };
  }

  return (
    <div style={{ border: '1px solid var(--sidebar-border, #d9d9d9)', borderRadius: 6, padding: '12px 12px 0', marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <Typography.Text type="secondary" strong>
          Image Generation
        </Typography.Text>
        <Tag color={statusBadge.color} style={{ margin: 0 }}>
          {statusBadge.text}
        </Tag>
      </div>

      {archKnown ? (
        <>
          <CommonImageGenFields />
          {isFlux && <FluxFields />}
        </>
      ) : (
        <Tabs
          size="small"
          items={[
            {
              key: 'sdxl',
              label: 'SD / SDXL',
              children: <CommonImageGenFields />,
            },
            {
              key: 'flux',
              label: 'Flux',
              children: (
                <>
                  <CommonImageGenFields />
                  <FluxFields />
                </>
              ),
            },
          ]}
        />
      )}
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────

export default function AgentsTab() {
  const { data: project } = useProject();
  const updateProject = useUpdateProject();
  const { data: modelsList } = useModels();
  const { data: lorasList } = useLoras();
  const { data: imagegenModels } = useImagegenModels();
  const agents: Agent[] = project?.agents ?? [];
  const users = useMemo(() => project?.users ?? [], [project?.users]);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [form] = Form.useForm<AgentFormValues>();
  const [selectedAgentType, setSelectedAgentType] = useState<AgentType | null>(null);

  const modelOptions = useMemo(
    () => (modelsList ?? []).map((m) => ({ label: `${m.name} (${m.model_identifier})`, value: m.id })),
    [modelsList],
  );

  const loraOptions = useMemo(
    () => (lorasList ?? []).map((l) => ({ label: `${l.name} (${l.base_model_id})`, value: l.id })),
    [lorasList],
  );

  const userOptions = useMemo(
    () => users.map((u) => ({ label: u.display_name || u.email || u.id, value: u.id })),
    [users],
  );

  const openAddModal = () => {
    setEditingAgent(null);
    setSelectedAgentType(null);
    form.resetFields();
    form.setFieldsValue({ notify_on_waiting: false });
    setModalOpen(true);
  };

  const openEditModal = (agent: Agent) => {
    setEditingAgent(agent);
    setSelectedAgentType(agent.agent_type as AgentType);
    form.setFieldsValue({
      id: agent.id,
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
      num_inference_steps: agent.num_inference_steps ?? undefined,
      guidance_scale: agent.guidance_scale ?? undefined,
      negative_prompt: agent.negative_prompt ?? undefined,
      num_images: agent.num_images ?? undefined,
      default_draft: agent.default_draft ?? undefined,
      max_sequence_length: agent.max_sequence_length ?? undefined,
      true_cfg_scale: agent.true_cfg_scale ?? undefined,
    });
    setModalOpen(true);
  };

  const handleCancel = () => {
    setModalOpen(false);
    setEditingAgent(null);
    setSelectedAgentType(null);
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
      const agentId = editingAgent
        ? editingAgent.id
        : (values.id?.trim() || toSlug(values.name));
      const isImageGen = values.agent_type === 'image_gen';
      const agentData: Agent = {
        id: agentId,
        name: values.name,
        agent_type: values.agent_type,
        model_id: values.model_id,
        lora_id: values.lora_id || null,
        prompt_template: values.prompt_template || null,
        temperature: values.temperature ?? null,
        context_length_override: values.context_length_override ?? null,
        cli_command: values.agent_type === 'tool' ? (values.cli_command || null) : null,
        linked_user_id: values.linked_user_id || null,
        notify_on_waiting: values.notify_on_waiting ?? false,
        num_inference_steps: isImageGen ? (values.num_inference_steps ?? null) : null,
        guidance_scale: isImageGen ? (values.guidance_scale ?? null) : null,
        negative_prompt: isImageGen ? (values.negative_prompt || null) : null,
        num_images: isImageGen ? (values.num_images ?? null) : null,
        default_draft: isImageGen ? (values.default_draft ?? null) : null,
        max_sequence_length: isImageGen ? (values.max_sequence_length ?? null) : null,
        true_cfg_scale: isImageGen ? (values.true_cfg_scale ?? null) : null,
      };

      let updatedAgents: Agent[];
      if (editingAgent) {
        updatedAgents = agents.map((a) => (a.id === editingAgent.id ? agentData : a));
      } else {
        // Check for duplicate ID
        if (agents.some((a) => a.id === agentId)) {
          message.error(`Agent ID "${agentId}" already exists`);
          return;
        }
        updatedAgents = [...agents, agentData];
      }

      saveAgents(updatedAgents);
      setModalOpen(false);
      setEditingAgent(null);
      setSelectedAgentType(null);
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
            name="id"
            label="Agent ID"
            tooltip="A short, readable identifier (auto-generated from name if left blank). Cannot be changed after creation."
            rules={editingAgent ? [] : [
              {
                validator: (_, value) => {
                  if (!value) return Promise.resolve(); // auto-generated
                  if (/^[a-z0-9][a-z0-9-]*$/.test(value)) return Promise.resolve();
                  return Promise.reject('ID must be lowercase alphanumeric with hyphens');
                },
              },
            ]}
          >
            <Input
              placeholder="e.g. primary-llm (auto from name if blank)"
              disabled={!!editingAgent}
            />
          </Form.Item>

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
            <Select
              placeholder="Select agent type"
              options={AGENT_TYPE_OPTIONS}
              onChange={(val: AgentType) => setSelectedAgentType(val)}
            />
          </Form.Item>

          <Form.Item
            name="model_id"
            label="Model"
            rules={[{ required: true, message: 'Model is required' }]}
          >
            <Select
              placeholder="Select a model"
              options={modelOptions}
              showSearch
              optionFilterProp="label"
              allowClear
            />
          </Form.Item>

          <Form.Item name="lora_id" label="LoRA Adapter">
            <Select
              placeholder="None"
              options={loraOptions}
              showSearch
              optionFilterProp="label"
              allowClear
            />
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

          {selectedAgentType === 'tool' && (
            <Form.Item name="cli_command" label="CLI Command">
              <Input placeholder="Command to execute for this tool agent" />
            </Form.Item>
          )}

          {selectedAgentType === 'image_gen' && (
            <Form.Item noStyle dependencies={['model_id']}>
              {() => {
                const mid = form.getFieldValue('model_id');
                const modelEntry = (modelsList ?? []).find((m) => m.id === mid);
                return (
                  <ImageGenFields
                    modelId={mid}
                    imagegenModels={imagegenModels}
                    modelDownloadStatus={modelEntry?.download_status}
                  />
                );
              }}
            </Form.Item>
          )}

          <Form.Item name="linked_user_id" label="Linked User">
            <Select
              placeholder="None"
              options={userOptions}
              showSearch
              optionFilterProp="label"
              allowClear
            />
          </Form.Item>

          <Form.Item name="notify_on_waiting" label="Notify on Waiting" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
