import { Typography } from 'antd';
import { TASK_STATUS_LABELS } from '../../types/config';
import type { TaskStatus } from '../../types/config';

const { Text } = Typography;

interface BoardHeaderProps {
  enabledStages: string[];
}

export default function BoardHeader({ enabledStages }: BoardHeaderProps) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${enabledStages.length}, minmax(140px, 1fr))`,
        gap: 0,
        position: 'sticky',
        top: 0,
        zIndex: 10,
        background: '#fff',
        borderBottom: '2px solid #e8e8e8',
      }}
    >
      {enabledStages.map((stage) => (
        <div
          key={stage}
          style={{
            padding: '8px 8px',
            textAlign: 'center',
            borderRight: '1px solid #f0f0f0',
          }}
        >
          <Text strong style={{ fontSize: 12, textTransform: 'uppercase' }}>
            {TASK_STATUS_LABELS[stage as TaskStatus] || stage}
          </Text>
        </div>
      ))}
    </div>
  );
}
