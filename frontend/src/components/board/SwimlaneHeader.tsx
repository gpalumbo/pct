import { memo, useCallback } from 'react';
import { Typography, Badge, Select, App } from 'antd';
import { useUpdateFeature } from '../../hooks/useBoardQueries';
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

function SwimlaneHeaderInner({ feature }: SwimlaneHeaderProps) {
  const taskCount = feature.tasks.length;
  const { message } = App.useApp();
  const updateFeature = useUpdateFeature();

  const handleStageChange = useCallback(
    (stage: FeatureStage) => {
      updateFeature.mutate(
        { featureId: feature.id, data: { stage } },
        { onError: () => message.error('Failed to update feature stage') },
      );
    },
    [updateFeature, feature.id, message],
  );

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
        <Text strong ellipsis className="pct-text-md">
          {feature.title}
        </Text>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <Select
            value={feature.stage}
            onChange={handleStageChange}
            size="small"
            variant="borderless"
            className="pct-text-xs"
            style={{ width: 110 }}
            popupMatchSelectWidth={false}
          >
            {FEATURE_STAGES.map((s) => (
              <Select.Option key={s.value} value={s.value}>
                <span className="pct-text-sm" style={{ color: s.color }}>{s.label}</span>
              </Select.Option>
            ))}
          </Select>
          <Badge
            count={taskCount}
            className="pct-text-xs"
            style={{ backgroundColor: 'var(--pct-color-text-muted)' }}
            size="small"
            title={`${taskCount} task${taskCount !== 1 ? 's' : ''}`}
          />
        </div>
      </div>
    </div>
  );
}

const SwimlaneHeader = memo(SwimlaneHeaderInner);
export default SwimlaneHeader;
