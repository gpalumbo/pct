import { Button, Space, Tag, Typography } from 'antd';
import {
  CaretDownOutlined,
  CaretRightOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import type { Feature } from '../../types/board';

const { Text } = Typography;

const STAGE_COLORS: Record<string, string> = {
  planning: 'blue',
  active: 'green',
  suspended: 'orange',
  'integration-test': 'purple',
  complete: 'default',
};

interface SwimlaneHeaderProps {
  feature: Feature;
  collapsed: boolean;
  onToggle: () => void;
  onSuspend: () => void;
  onResume: () => void;
}

export default function SwimlaneHeader({
  feature,
  collapsed,
  onToggle,
  onSuspend,
  onResume,
}: SwimlaneHeaderProps) {
  const stage = feature.metadata.lifecycle_stage;
  const totalTasks = feature.tasks.length;
  const doneTasks = feature.tasks.filter((t) => t.status === 'done').length;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '4px 8px',
        background: '#fafafa',
        borderBottom: '1px solid #f0f0f0',
        cursor: 'pointer',
        userSelect: 'none',
      }}
      onClick={onToggle}
    >
      {collapsed ? <CaretRightOutlined /> : <CaretDownOutlined />}
      <Text strong style={{ fontSize: 13 }}>
        {feature.title}
      </Text>
      <Tag color={STAGE_COLORS[stage] || 'default'} style={{ margin: 0 }}>
        {stage}
      </Tag>
      {totalTasks > 0 && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {doneTasks}/{totalTasks}
        </Text>
      )}
      <Space style={{ marginLeft: 'auto' }} onClick={(e) => e.stopPropagation()}>
        {stage !== 'suspended' ? (
          <Button
            size="small"
            type="text"
            icon={<PauseCircleOutlined />}
            onClick={onSuspend}
          >
            Suspend
          </Button>
        ) : (
          <Button
            size="small"
            type="text"
            icon={<PlayCircleOutlined />}
            onClick={onResume}
          >
            Resume
          </Button>
        )}
      </Space>
    </div>
  );
}
