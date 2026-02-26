import { useState } from 'react';
import { Input } from 'antd';
import type { Feature } from '../../types/board';
import { useBoardStore } from '../../stores/boardStore';
import { useSuspendFeature, useResumeFeature, useCreateTask } from '../../hooks/useBoardQueries';
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
  const createTask = useCreateTask();

  const [addingTask, setAddingTask] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState('');

  const handleAddTask = () => {
    // Expand swimlane if collapsed
    if (collapsed) {
      toggleSwimlane(feature.id);
    }
    setAddingTask(true);
    setNewTaskTitle('');
  };

  // Infer default artifact_type from sibling tasks in this feature
  const inferredArtifactType = (() => {
    const types = feature.tasks.map((t) => t.artifact_type).filter((t) => t && t !== 'text');
    if (types.length > 0) return types[0];
    return 'text';
  })();

  const handleSubmitTask = () => {
    const title = newTaskTitle.trim();
    if (!title) {
      setAddingTask(false);
      return;
    }
    const firstStage = enabledStages[0] || 'todo';
    createTask.mutate(
      {
        featureId: feature.id,
        data: { title, status: firstStage, artifact_type: inferredArtifactType },
      },
      {
        onSuccess: () => {
          setAddingTask(false);
          setNewTaskTitle('');
        },
      },
    );
  };

  const handleCancelTask = () => {
    setAddingTask(false);
    setNewTaskTitle('');
  };

  return (
    <div style={{ borderBottom: '1px solid #e8e8e8' }}>
      <SwimlaneHeader
        feature={feature}
        collapsed={collapsed}
        onToggle={() => toggleSwimlane(feature.id)}
        onSuspend={() => suspendFeature.mutate(feature.id)}
        onResume={() => resumeFeature.mutate(feature.id)}
        onAddTask={handleAddTask}
      />
      {addingTask && !collapsed && (
        <div style={{ padding: '4px 8px', background: '#fafafa' }}>
          <Input
            size="small"
            placeholder="Task title… (Enter to create, Escape to cancel)"
            value={newTaskTitle}
            onChange={(e) => setNewTaskTitle(e.target.value)}
            onPressEnter={handleSubmitTask}
            onKeyDown={(e) => {
              if (e.key === 'Escape') handleCancelTask();
            }}
            autoFocus
            disabled={createTask.isPending}
          />
        </div>
      )}
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
