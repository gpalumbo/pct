import { DragDropContext, type DropResult } from '@hello-pangea/dnd';
import { Spin, Typography } from 'antd';
import { useBoard, useMoveTask, useReassignTask } from '../../hooks/useBoardQueries';
import { useBoardStore } from '../../stores/boardStore';
import type { Feature } from '../../types/board';
import BoardHeader from './BoardHeader';
import BoardToolbar from './BoardToolbar';
import Swimlane from './Swimlane';
import BacklogSection from './BacklogSection';
import StageSkipModal from './StageSkipModal';

const { Text } = Typography;

export default function KanbanBoard() {
  const { data: board, isLoading, refetch } = useBoard();
  const moveTask = useMoveTask();
  const reassignTask = useReassignTask();
  const setPendingMove = useBoardStore((s) => s.setPendingMove);
  const setIsDragging = useBoardStore((s) => s.setIsDragging);
  const filterFeatureIds = useBoardStore((s) => s.filterFeatureIds);
  const showSuspended = useBoardStore((s) => s.showSuspended);
  const showComplete = useBoardStore((s) => s.showComplete);

  if (isLoading || !board) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    );
  }

  const enabledStages = board.enabled_stages;

  // Filter features
  let visibleFeatures: Feature[] = board.features;
  if (filterFeatureIds.length > 0) {
    visibleFeatures = visibleFeatures.filter((f) => filterFeatureIds.includes(f.id));
  }
  if (!showSuspended) {
    visibleFeatures = visibleFeatures.filter(
      (f) => f.metadata.lifecycle_stage !== 'suspended',
    );
  }
  if (!showComplete) {
    visibleFeatures = visibleFeatures.filter(
      (f) => f.metadata.lifecycle_stage !== 'complete',
    );
  }

  const handleDragStart = () => setIsDragging(true);

  const handleDragEnd = (result: DropResult) => {
    setIsDragging(false);
    if (!result.destination) return;

    const [srcFeature] = result.draggableId.split(':');
    const [, srcStage] = result.source.droppableId.split(':');
    const [destFeature, destStage] = result.destination.droppableId.split(':');

    if (srcStage === destStage && srcFeature === destFeature) return;

    const taskId = result.draggableId.split(':')[1];

    // Cross-feature move: reassign task (skip adjacency check)
    if (srcFeature !== destFeature) {
      reassignTask.mutate({
        src_feature_id: srcFeature,
        task_id: taskId,
        dest_feature_id: destFeature,
        new_status: destStage,
      });
      return;
    }

    // Same-feature move: check adjacency
    const srcIdx = enabledStages.indexOf(srcStage);
    const destIdx = enabledStages.indexOf(destStage);
    const isAdjacent = Math.abs(destIdx - srcIdx) <= 1;

    if (isAdjacent) {
      moveTask.mutate({
        featureId: srcFeature,
        taskId,
        data: { new_status: destStage },
      });
    } else {
      // Open confirmation modal
      setPendingMove({
        featureId: srcFeature,
        taskId,
        newStatus: destStage,
      });
    }
  };

  if (enabledStages.length === 0) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <Text type="secondary">
          No workflow stages configured. Go to Settings to enable workflow stages.
        </Text>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <BoardToolbar features={board.features} onRefresh={() => refetch()} />
      <div style={{ flex: 1, overflow: 'auto' }}>
        <BoardHeader enabledStages={enabledStages} />
        <DragDropContext onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
          {visibleFeatures.map((feature) => (
            <Swimlane
              key={feature.id}
              feature={feature}
              enabledStages={enabledStages}
            />
          ))}
        </DragDropContext>
        <BacklogSection backlog={board.backlog} />
      </div>
      <StageSkipModal />
    </div>
  );
}
