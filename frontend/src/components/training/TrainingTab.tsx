import { Typography, Form, Input, Select, InputNumber, Button, Collapse, Alert, Space } from 'antd';
import { ExperimentOutlined } from '@ant-design/icons';
import { useDatasets } from '../../hooks/useTrainingQueries';
import type { TrainingMethod, LoRASaveTarget } from '../../types/enums';

const { Title } = Typography;

const TRAINING_METHODS: { label: string; value: TrainingMethod }[] = [
  { label: 'SFT (Supervised Fine-Tuning)', value: 'sft' },
  { label: 'KTO (Kahneman-Tversky Optimization)', value: 'kto' },
];

const SAVE_TARGETS: { label: string; value: LoRASaveTarget }[] = [
  { label: 'Project Local', value: 'project_local' },
  { label: 'Global', value: 'global' },
];

export default function TrainingTab() {
  const { data: datasets } = useDatasets();
  const [form] = Form.useForm();

  const datasetOptions = (datasets ?? []).map((ds) => ({
    label: `${ds.name} (${ds.entries.length} entries)`,
    value: ds.id,
  }));

  const hyperparameterItems = [
    {
      key: 'hyperparams',
      label: 'Hyperparameters',
      children: (
        <>
          <Form.Item name="lora_rank" label="LoRA Rank" initialValue={16}>
            <InputNumber min={4} max={128} step={4} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="lora_alpha" label="LoRA Alpha" initialValue={32}>
            <InputNumber min={4} max={256} step={4} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="learning_rate" label="Learning Rate" initialValue={0.0002}>
            <InputNumber min={0.00001} max={0.01} step={0.00001} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="epochs" label="Epochs" initialValue={3}>
            <InputNumber min={1} max={50} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="batch_size" label="Batch Size" initialValue={4}>
            <InputNumber min={1} max={64} style={{ width: '100%' }} />
          </Form.Item>
        </>
      ),
    },
  ];

  return (
    <div>
      <Title level={5}>Training Job Configuration</Title>

      <Alert
        message="GPU training not yet available"
        description="Training requires a compatible GPU. This form allows you to configure jobs in advance."
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Form form={form} layout="vertical" style={{ maxWidth: 600 }}>
        <Form.Item
          name="name"
          label="Job Name"
          rules={[{ required: true, message: 'Name is required' }]}
        >
          <Input placeholder="e.g. style-lora-v1" />
        </Form.Item>

        <Form.Item
          name="base_model_id"
          label="Base Model"
          rules={[{ required: true, message: 'Base model is required' }]}
        >
          <Input placeholder="Model ID from registry" />
        </Form.Item>

        <Form.Item
          name="training_method"
          label="Training Method"
          rules={[{ required: true, message: 'Method is required' }]}
        >
          <Select options={TRAINING_METHODS} placeholder="Select method" />
        </Form.Item>

        <Form.Item
          name="dataset_ids"
          label="Datasets"
          rules={[{ required: true, message: 'At least one dataset is required' }]}
        >
          <Select
            mode="multiple"
            options={datasetOptions}
            placeholder="Select datasets"
            notFoundContent="No datasets available"
          />
        </Form.Item>

        <Form.Item name="target_lora_name" label="Target LoRA Name">
          <Input placeholder="e.g. my-style-lora" />
        </Form.Item>

        <Form.Item name="save_target" label="Save Target" initialValue="project_local">
          <Select options={SAVE_TARGETS} />
        </Form.Item>

        <Collapse items={hyperparameterItems} style={{ marginBottom: 24 }} />

        <Form.Item>
          <Space>
            <Button type="primary" icon={<ExperimentOutlined />} disabled>
              Start Training
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </div>
  );
}
