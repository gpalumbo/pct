import { useEffect } from 'react';
import { Button, Divider, Form, Input, InputNumber, Select, Slider, Switch, Typography, message } from 'antd';
import { useProjectConfig, useSaveProjectConfig, useAgents } from '../../hooks/useConfigQueries';
import { useUIStore } from '../../stores/uiStore';
import type { ProjectConfig } from '../../types/config';

const DEFAULT_CONFIG: ProjectConfig = {
  project_id: '',
  project_name: '',
  project_type: '',
  agents: [],
  workflow_stages: [],
  planning_agent: '',
  default_agent: '',
  auto_advance: true,
  concurrency: { remote_api_limit: 2, local_gpu_limit: 1 },
  context: { token_budget: 8000, context_manager_model: '' },
};

export default function GeneralTab() {
  const { data: config } = useProjectConfig();
  const { data: agents = [] } = useAgents();
  const saveConfig = useSaveProjectConfig();
  const [form] = Form.useForm();

  useEffect(() => {
    if (config) {
      form.setFieldsValue(config);
    }
  }, [config, form]);

  const handleSave = async () => {
    const values = await form.validateFields();
    // Merge form values with existing config to preserve agents/stages
    const merged: ProjectConfig = {
      ...DEFAULT_CONFIG,
      ...config,
      ...values,
      concurrency: { ...DEFAULT_CONFIG.concurrency, ...config?.concurrency, ...values.concurrency },
      context: { ...DEFAULT_CONFIG.context, ...config?.context, ...values.context },
    };
    await saveConfig.mutateAsync(merged);
    message.success('Project config saved');
  };

  const fontSize = useUIStore((s) => s.fontSize);
  const setFontSize = useUIStore((s) => s.setFontSize);

  const agentOptions = agents.map((a) => ({ label: a.id, value: a.id }));

  return (
    <div style={{ maxWidth: 600 }}>
      <Divider orientation="left">UI Preferences</Divider>
      <div style={{ marginBottom: 24 }}>
        <Typography.Text>Font Size: {fontSize}px</Typography.Text>
        <Slider min={10} max={20} value={fontSize} onChange={setFontSize} />
      </div>

    <Form form={form} layout="vertical" initialValues={config ?? DEFAULT_CONFIG}>
      <Divider orientation="left">Project Metadata</Divider>
      <Form.Item name="project_id" label="Project ID">
        <Input />
      </Form.Item>
      <Form.Item name="project_name" label="Project Name">
        <Input />
      </Form.Item>
      <Form.Item name="project_type" label="Project Type">
        <Input placeholder="e.g. python, typescript, rust" />
      </Form.Item>

      <Divider orientation="left">Planning & Defaults</Divider>
      <Form.Item name="planning_agent" label="Planning Agent">
        <Select allowClear options={agentOptions} placeholder="Select agent" />
      </Form.Item>
      <Form.Item name="default_agent" label="Default Agent">
        <Select allowClear options={agentOptions} placeholder="Select agent" />
      </Form.Item>
      <Form.Item name="auto_advance" label="Auto Advance" valuePropName="checked">
        <Switch />
      </Form.Item>

      <Divider orientation="left">Concurrency</Divider>
      <Form.Item name={['concurrency', 'remote_api_limit']} label="Remote API Limit">
        <InputNumber min={1} style={{ width: '100%' }} />
      </Form.Item>
      <Form.Item name={['concurrency', 'local_gpu_limit']} label="Local GPU Limit">
        <InputNumber min={1} style={{ width: '100%' }} />
      </Form.Item>

      <Divider orientation="left">Context</Divider>
      <Form.Item name={['context', 'token_budget']} label="Token Budget">
        <InputNumber min={1} style={{ width: '100%' }} />
      </Form.Item>
      <Form.Item name={['context', 'context_manager_model']} label="Context Manager Model">
        <Input placeholder="e.g. gpt-3.5-turbo" />
      </Form.Item>

      <Form.Item>
        <Button type="primary" onClick={handleSave} loading={saveConfig.isPending}>
          Save Project Config
        </Button>
      </Form.Item>
    </Form>
    </div>
  );
}
