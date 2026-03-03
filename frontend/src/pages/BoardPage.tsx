import { useState } from 'react';
import BoardHeader from '../components/board/BoardHeader';
import BoardToolbar from '../components/board/BoardToolbar';
import KanbanBoard from '../components/board/KanbanBoard';
import TaskDetailPanel from '../components/board/TaskDetailPanel';
import { useBoardStore } from '../stores/boardStore';

export default function BoardPage() {
  const [searchText, setSearchText] = useState('');
  const [stageFilter, setStageFilter] = useState<string | null>(null);

  const features = useBoardStore((s) => s.features);
  const workflowStages = useBoardStore((s) => s.workflowStages);
  const selectedFeatureId = useBoardStore((s) => s.selectedFeatureId);
  const selectedTaskId = useBoardStore((s) => s.selectedTaskId);

  const selectedFeature = features.find((f) => f.id === selectedFeatureId);
  const selectedTask = selectedFeature?.tasks.find((t) => t.id === selectedTaskId) ?? null;

  const stageOptions = workflowStages
    .filter((s) => s.enabled)
    .map((s) => ({ value: s.id, label: s.label }));

  return (
    <div style={{ padding: 16, height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
      <BoardHeader />
      <BoardToolbar
        searchText={searchText}
        onSearchChange={setSearchText}
        stageFilter={stageFilter}
        onStageFilterChange={setStageFilter}
        stageOptions={stageOptions}
      />
      <div style={{ flex: 1, overflow: 'auto' }}>
        <KanbanBoard />
      </div>
      <TaskDetailPanel
        task={selectedTask}
        featureId={selectedFeatureId}
        stages={workflowStages}
      />
    </div>
  );
}
