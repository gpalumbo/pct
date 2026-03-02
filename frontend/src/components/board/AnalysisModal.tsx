import { Modal, Typography, Empty } from 'antd';

const { Text } = Typography;

interface AnalysisModalProps {
  open: boolean;
  onClose: () => void;
}

export default function AnalysisModal({ open, onClose }: AnalysisModalProps) {
  return (
    <Modal
      open={open}
      title="Board Analysis"
      onCancel={onClose}
      footer={null}
      width={700}
    >
      <Empty description="Analysis not yet available" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      <Text type="secondary" style={{ display: 'block', textAlign: 'center', marginTop: 8 }}>
        Board analysis and consistency checks will be displayed here.
      </Text>
    </Modal>
  );
}
