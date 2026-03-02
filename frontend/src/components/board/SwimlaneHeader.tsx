import { Typography, Tag, Badge } from 'antd';
import type { Feature } from '../../types/board';

const { Text } = Typography;

const stageColors: Record<string, string> = {
  planning: 'blue',
  active: 'green',
  suspended: 'orange',
  integration_test: 'purple',
  complete: 'default',
};

interface SwimlaneHeaderProps {
  feature: Feature;
}

export default function SwimlaneHeader({ feature }: SwimlaneHeaderProps) {
  const taskCount = feature.tasks.length;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '6px 0',
        minWidth: 160,
        maxWidth: 160,
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2, overflow: 'hidden' }}>
        <Text strong ellipsis style={{ fontSize: 13 }}>
          {feature.title}
        </Text>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <Tag color={stageColors[feature.stage] ?? 'default'} style={{ fontSize: 10, margin: 0 }}>
            {feature.stage.replace('_', ' ')}
          </Tag>
          <Badge
            count={taskCount}
            style={{ backgroundColor: '#8c8c8c', fontSize: 10 }}
            size="small"
            title={`${taskCount} task${taskCount !== 1 ? 's' : ''}`}
          />
        </div>
      </div>
    </div>
  );
}
