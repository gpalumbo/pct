import { Typography, Badge, Select, App } from 'antd';
import { boardApi } from '../../api/boardApi';
import { useQueryClient } from '@tanstack/react-query';
import type { Feature } from '../../types/board';
import type { FeatureStage } from '../../types/enums';

const { Text } = Typography;

const FEATURE_STAGES: { value: FeatureStage; label: string; color: string }[] = [
  { value: 'planning', label: 'Planning', color: '#1890ff' },
  { value: 'active', label: 'Active', color: '#52c41a' },
  { value: 'suspended', label: 'Suspended', color: '#faad14' },
  { value: 'integration_test', label: 'Integration Test', color: '#722ed1' },
  { value: 'complete', label: 'Complete', color: '#8c8c8c' },
];

interface SwimlaneHeaderProps {
  feature: Feature;
}

export default function SwimlaneHeader({ feature }: SwimlaneHeaderProps) {
  const taskCount = feature.tasks.length;
  const { message } = App.useApp();
  const qc = useQueryClient();

  const handleStageChange = async (stage: FeatureStage) => {
    try {
      await boardApi.updateFeature(feature.id, { stage });
      qc.invalidateQueries({ queryKey: ['board'] });
    } catch {
      message.error('Failed to update feature stage');
    }
  };

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
          <Select
            value={feature.stage}
            onChange={handleStageChange}
            size="small"
            variant="borderless"
            style={{ width: 110, fontSize: 10 }}
            popupMatchSelectWidth={false}
          >
            {FEATURE_STAGES.map((s) => (
              <Select.Option key={s.value} value={s.value}>
                <span style={{ color: s.color, fontSize: 11 }}>{s.label}</span>
              </Select.Option>
            ))}
          </Select>
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
