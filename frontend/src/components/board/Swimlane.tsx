import type { Feature } from '../../types/board';
import { useBoardStore } from '../../stores/boardStore';
import { useSuspendFeature, useResumeFeature } from '../../hooks/useBoardQueries';
import SwimlaneHeader from './SwimlaneHeader';
import StageColumn from './StageColumn';

interface SwimlaneProps {
  feature: Feature;
  enabledStages: string[];
}

export default function Swimlane({ feature, enabledStages }: SwimlaneProps) {
  const collapsed = useBoardStore((s) => s.collapsedSwimlanes.has(feature.id));
  const toggleSwimlane = useBoardStore((s) => s.toggleSwimlane);
  const suspendFeature = useSuspendFeature();
  const resumeFeature = useResumeFeature();

  return (
    <div style={{ borderBottom: '1px solid #e8e8e8' }}>
      <SwimlaneHeader
        feature={feature}
        collapsed={collapsed}
        onToggle={() => toggleSwimlane(feature.id)}
        onSuspend={() => suspendFeature.mutate(feature.id)}
        onResume={() => resumeFeature.mutate(feature.id)}
      />
      {!collapsed && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: `repeat(${enabledStages.length}, minmax(140px, 1fr))`,
            gap: 0,
          }}
        >
          {enabledStages.map((stage) => (
            <StageColumn
              key={stage}
              featureId={feature.id}
              stage={stage}
              tasks={feature.tasks.filter((t) => t.status === stage)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
