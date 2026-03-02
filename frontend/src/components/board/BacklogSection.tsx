import { Collapse, Typography, Empty } from 'antd';
import type { Feature } from '../../types/board';

const { Text } = Typography;

interface BacklogSectionProps {
  features: Feature[];
}

export default function BacklogSection({ features }: BacklogSectionProps) {
  const planningFeatures = features.filter((f) => f.stage === 'planning');

  if (planningFeatures.length === 0) return null;

  return (
    <Collapse
      size="small"
      style={{ marginBottom: 12 }}
      items={[
        {
          key: 'backlog',
          label: (
            <Text strong>
              Backlog / Planning ({planningFeatures.length})
            </Text>
          ),
          children:
            planningFeatures.length === 0 ? (
              <Empty description="No features in backlog" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {planningFeatures.map((f) => (
                  <div key={f.id} style={{ padding: '4px 8px', background: '#fafafa', borderRadius: 4 }}>
                    <Text>{f.title}</Text>
                    <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                      {f.tasks.length} task{f.tasks.length !== 1 ? 's' : ''}
                    </Text>
                  </div>
                ))}
              </div>
            ),
        },
      ]}
    />
  );
}
