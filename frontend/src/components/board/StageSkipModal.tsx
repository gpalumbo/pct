import { Modal, Typography } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface StageSkipModalProps {
  open: boolean;
  fromStage: string;
  toStage: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function StageSkipModal({ open, fromStage, toStage, onConfirm, onCancel }: StageSkipModalProps) {
  return (
    <Modal
      open={open}
      title={
        <span>
          <ExclamationCircleOutlined style={{ color: 'var(--pct-color-warning)', marginRight: 8 }} />
          Skip Stage Confirmation
        </span>
      }
      onOk={onConfirm}
      onCancel={onCancel}
      okText="Skip Stage"
      okButtonProps={{ danger: true }}
    >
      <Text>
        You are about to move this task from <Text strong>{fromStage}</Text> to{' '}
        <Text strong>{toStage}</Text>, skipping one or more intermediate stages.
      </Text>
      <br />
      <br />
      <Text type="secondary">
        Skipped stages will be marked as bypassed. Are you sure you want to continue?
      </Text>
    </Modal>
  );
}
