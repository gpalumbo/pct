import { Modal, Empty, Typography } from 'antd';

const { Text } = Typography;

interface ImageGalleryModalProps {
  open: boolean;
  featureId: string;
  taskId: string;
  onClose: () => void;
}

export default function ImageGalleryModal({ open, featureId: _featureId, taskId: _taskId, onClose }: ImageGalleryModalProps) {
  return (
    <Modal
      open={open}
      title="Image Gallery"
      onCancel={onClose}
      footer={null}
      width={800}
    >
      <Empty description="No generated images yet" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      <Text type="secondary" style={{ display: 'block', textAlign: 'center', marginTop: 8 }}>
        Generated images for this task will appear here.
      </Text>
    </Modal>
  );
}
