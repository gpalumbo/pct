import { useEffect, useState } from 'react';
import {
  Form,
  Input,
  Slider,
  InputNumber,
  Button,
  Spin,
  App,
  Select,
  Radio,
  Card,
  Switch,
  Tag,
  Typography,
} from 'antd';
import { useProject, useUpdateProject, useInitializeProject } from '../../hooks/useConfigQueries';
import type { Project, SmtpConfig } from '../../types/config';

const { Text } = Typography;
const { TextArea } = Input;

function InitForm() {
  const { message } = App.useApp();
  const [name, setName] = useState('');
  const [projectType, setProjectType] = useState('coding');
  const initProject = useInitializeProject();

  const handleSubmit = async () => {
    if (!name.trim()) {
      message.warning('Project name is required');
      return;
    }
    try {
      await initProject.mutateAsync({ name: name.trim(), projectType });
      message.success('Project initialized');
    } catch {
      message.error('Failed to initialize project');
    }
  };

  return (
    <Card title="Initialize Project" style={{ maxWidth: 500 }}>
      <Form layout="vertical" onFinish={handleSubmit}>
        <Form.Item label="Project Name" required>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My Project"
          />
        </Form.Item>
        <Form.Item label="Project Type">
          <Radio.Group value={projectType} onChange={(e) => setProjectType(e.target.value)}>
            <Radio value="coding">Coding</Radio>
            <Radio value="writing">Writing</Radio>
          </Radio.Group>
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={initProject.isPending}>
            Create Project
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
}

function EditForm({ project }: { project: Project }) {
  const { message } = App.useApp();
  const updateProject = useUpdateProject();
  const [form] = Form.useForm();

  const agentOptions = (project.agents ?? []).map((a) => ({
    label: a.name,
    value: a.id,
  }));

  useEffect(() => {
    form.setFieldsValue({
      name: project.name,
      default_agent_id: project.default_agent_id || undefined,
      planning_agent_id: project.planning_agent_id || undefined,
      context_manager_agent_id: project.context_manager_agent_id ?? undefined,
      context_manager_prompt: project.context_manager_prompt ?? '',
      font_size: project.font_size,
      max_remote_agents: project.max_remote_agents,
      max_local_agents: project.max_local_agents,
      notification_email: project.notification_email ?? '',
      smtp_server: project.smtp_config?.server ?? '',
      smtp_port: project.smtp_config?.port ?? 587,
      smtp_username: project.smtp_config?.username ?? '',
      smtp_password: project.smtp_config?.password ?? '',
      smtp_tls: project.smtp_config?.tls ?? true,
    });
  }, [project, form]);

  const onFinish = async (values: Record<string, unknown>) => {
    let smtpConfig: SmtpConfig | null = null;
    const smtpServer = values.smtp_server as string;
    if (smtpServer) {
      smtpConfig = {
        server: smtpServer,
        port: values.smtp_port as number,
        username: values.smtp_username as string,
        password: values.smtp_password as string,
        tls: values.smtp_tls as boolean,
      };
    }

    const updated: Project = {
      ...project,
      name: values.name as string,
      default_agent_id: (values.default_agent_id as string) ?? '',
      planning_agent_id: (values.planning_agent_id as string) ?? '',
      context_manager_agent_id: (values.context_manager_agent_id as string) || null,
      context_manager_prompt: (values.context_manager_prompt as string) || null,
      font_size: values.font_size as number,
      max_remote_agents: values.max_remote_agents as number,
      max_local_agents: values.max_local_agents as number,
      notification_email: (values.notification_email as string) || null,
      smtp_config: smtpConfig,
    };
    try {
      await updateProject.mutateAsync(updated);
      message.success('Project settings saved');
    } catch {
      message.error('Failed to save settings');
    }
  };

  return (
    <Form form={form} layout="vertical" onFinish={onFinish} style={{ maxWidth: 600 }}>
      <Form.Item name="name" label="Project Name" rules={[{ required: true, message: 'Project name is required' }]}>
        <Input />
      </Form.Item>

      <Form.Item label="Project Type">
        <Tag>{project.project_type}</Tag>
      </Form.Item>

      <Form.Item label="Directory">
        <Text code>{project.directory || '(not set)'}</Text>
      </Form.Item>

      <Form.Item name="default_agent_id" label="Default Agent">
        <Select options={agentOptions} allowClear placeholder="Select default agent" />
      </Form.Item>

      <Form.Item name="planning_agent_id" label="Planning Agent">
        <Select options={agentOptions} allowClear placeholder="Select planning agent" />
      </Form.Item>

      <Form.Item name="context_manager_agent_id" label="Context Manager Agent">
        <Select options={agentOptions} allowClear placeholder="(optional)" />
      </Form.Item>

      <Form.Item name="context_manager_prompt" label="Context Manager Prompt">
        <TextArea rows={3} placeholder="Prompt for context manager agent" />
      </Form.Item>

      <Form.Item name="font_size" label="Font Size">
        <Slider min={10} max={20} marks={{ 10: '10', 14: '14', 20: '20' }} />
      </Form.Item>

      <Form.Item name="max_remote_agents" label="Max Remote Agents">
        <InputNumber min={0} max={50} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item name="max_local_agents" label="Max Local Agents">
        <InputNumber min={0} max={20} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item name="notification_email" label="Notification Email">
        <Input type="email" placeholder="user@example.com" />
      </Form.Item>

      <Card title="SMTP Configuration" size="small" style={{ marginBottom: 24 }}>
        <Form.Item name="smtp_server" label="Server">
          <Input placeholder="smtp.example.com" />
        </Form.Item>
        <Form.Item name="smtp_port" label="Port">
          <InputNumber min={1} max={65535} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="smtp_username" label="Username">
          <Input />
        </Form.Item>
        <Form.Item name="smtp_password" label="Password">
          <Input.Password />
        </Form.Item>
        <Form.Item name="smtp_tls" label="TLS" valuePropName="checked">
          <Switch />
        </Form.Item>
      </Card>

      <Form.Item>
        <Button type="primary" htmlType="submit" loading={updateProject.isPending}>
          Save Settings
        </Button>
      </Form.Item>
    </Form>
  );
}

export default function GeneralTab() {
  const { data: project, isLoading } = useProject();

  if (isLoading) return <Spin />;

  if (!project?.initialized) return <InitForm />;

  return <EditForm project={project} />;
}
