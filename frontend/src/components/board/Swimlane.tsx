import SwimlaneHeader from './SwimlaneHeader';
import StageColumn from './StageColumn';
import type { Feature, WorkflowStage } from '../../types/board';

interface SwimlaneProps {
  feature: Feature;
  stages: WorkflowStage[];
}

export default function Swimlane({ feature, stages }: SwimlaneProps) {
  const enabledStages = stages.filter((s) => s.enabled);

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
        {enabledStages.map((stage) => {
          const tasks = feature.tasks.filter((t) => t.current_stage_id === stage.id);
          return (
            <StageColumn
              key={stage.id}
              stage={stage}
              tasks={tasks}
              featureId={feature.id}
            />
          );
        })}
      </div>
    </div>
  );
}
