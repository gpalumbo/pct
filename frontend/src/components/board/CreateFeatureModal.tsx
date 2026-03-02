import { Modal, Form, Input, message } from 'antd';
import { useCreateFeature } from '../../hooks/useBoardQueries';
import type { FeatureCreate } from '../../types/board';

interface CreateFeatureModalProps {
  open: boolean;
  onClose: () => void;
}

export default function CreateFeatureModal({ open, onClose }: CreateFeatureModalProps) {
  const [form] = Form.useForm();
  const createFeature = useCreateFeature();

  const onFinish = async () => {
    try {
      const values = await form.validateFields();
      const data: FeatureCreate = {
        id: crypto.randomUUID(),
        title: values.title,
        spec_content: values.spec_content,
      };
      await createFeature.mutateAsync(data);
      message.success('Feature created');
      form.resetFields();
      onClose();
    } catch {
      message.error('Failed to create feature');
    }
  };

  return (
    <Modal
      open={open}
      title="Create New Feature"
      onOk={onFinish}
      onCancel={onClose}
      confirmLoading={createFeature.isPending}
      okText="Create"
    >
      <Form form={form} layout="vertical">
        <Form.Item name="title" label="Feature Title" rules={[{ required: true, message: 'Title is required' }]}>
          <Input placeholder="e.g. User Authentication" />
        </Form.Item>
        <Form.Item name="spec_content" label="Spec Content (optional)">
          <Input.TextArea rows={6} placeholder="Initial specification content..." />
        </Form.Item>
      </Form>
    </Modal>
  );
}
