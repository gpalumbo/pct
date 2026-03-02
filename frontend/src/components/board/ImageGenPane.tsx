import { Typography, Button, Input, Empty } from 'antd';
import { PictureOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface ImageGenPaneProps {
  featureId: string;
  taskId: string;
}

export default function ImageGenPane({ featureId: _featureId, taskId: _taskId }: ImageGenPaneProps) {
  return (
    <div>
      <Title level={5}>Image Generation</Title>
      <TextArea rows={3} placeholder="Enter image generation prompt..." style={{ marginBottom: 8 }} />
      <Button icon={<PictureOutlined />} type="primary" disabled>
        Generate
      </Button>
      <div style={{ marginTop: 16 }}>
        <Empty description="Image generation coming soon" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        <Text type="secondary" style={{ display: 'block', textAlign: 'center', marginTop: 8 }}>
          Configure an image_gen agent in Settings to enable this feature.
        </Text>
      </div>
    </div>
  );
}
