import { memo, useMemo } from 'react';
import SwimlaneHeader from './SwimlaneHeader';
import StageColumn from './StageColumn';
import type { Feature, WorkflowStage } from '../../types/board';

interface SwimlaneProps {
  feature: Feature;
  stages: WorkflowStage[];
}

function SwimlaneInner({ feature, stages }: SwimlaneProps) {
  const enabledStages = useMemo(() => stages.filter((s) => s.enabled), [stages]);

  // Pre-compute task groups by stage to keep stable references for StageColumn memo
  const tasksByStage = useMemo(() => {
    const map = new Map<string, typeof feature.tasks>();
    for (const stage of enabledStages) {
      map.set(stage.id, feature.tasks.filter((t) => t.current_stage_id === stage.id));
    }
    return map;
  }, [feature.tasks, enabledStages]);

  return (
    <div
      style={{
        display: 'flex',
        gap: 8,
        padding: '8px 0',
        borderBottom: '1px solid #f0f0f0',
        alignItems: 'flex-start',
      }}
    >
      <SwimlaneHeader feature={feature} />
      <div style={{ display: 'flex', gap: 8, flex: 1, overflowX: 'auto' }}>
        {enabledStages.map((stage) => (
          <StageColumn
            key={stage.id}
            stage={stage}
            tasks={tasksByStage.get(stage.id) ?? []}
            featureId={feature.id}
          />
        ))}
      </div>
    </div>
  );
}

const Swimlane = memo(SwimlaneInner);
export default Swimlane;
