import { useState } from 'react';
import { Button, Card, Collapse, Typography } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import type { BacklogFeature } from '../../types/board';
import { useActivateBacklogFeature } from '../../hooks/useBoardQueries';

const { Text } = Typography;

interface BacklogSectionProps {
  backlog: BacklogFeature[];
}

export default function BacklogSection({ backlog }: BacklogSectionProps) {
  const [expanded, setExpanded] = useState(false);
  const activateMutation = useActivateBacklogFeature();

  if (backlog.length === 0) return null;

  return (
    <Collapse
      activeKey={expanded ? ['backlog'] : []}
      onChange={() => setExpanded(!expanded)}
      style={{ margin: '8px 0' }}
      items={[
        {
          key: 'backlog',
          label: (
            <Text strong>
              Backlog ({backlog.length})
            </Text>
          ),
          children: (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {backlog.map((feature) => (
                <Card key={feature.id} size="small" style={{ width: 220 }}>
                  <Text strong style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
                    {feature.title}
                  </Text>
                  <Button
                    size="small"
                    type="primary"
                    icon={<PlusOutlined />}
                    loading={activateMutation.isPending}
                    onClick={() => activateMutation.mutate(feature.id)}
                  >
                    Activate
                  </Button>
                </Card>
              ))}
            </div>
          ),
        },
      ]}
    />
  );
}
