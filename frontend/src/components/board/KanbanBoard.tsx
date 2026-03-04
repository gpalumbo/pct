import { useCallback, useEffect, useMemo } from 'react';
import { DragDropContext, type DropResult } from '@hello-pangea/dnd';
import { Spin, Empty, Typography } from 'antd';
import Swimlane from './Swimlane';
import { useBoardQuery, useMoveTaskDynamic } from '../../hooks/useBoardQueries';
import { useBoardStore } from '../../stores/boardStore';

const { Text } = Typography;

export default function KanbanBoard() {
  const { data: board, isLoading } = useBoardQuery();
  const setBoard = useBoardStore((s) => s.setBoard);
  const moveTask = useMoveTaskDynamic();

  // Keep store in sync with query data
  useEffect(() => {
    if (board) {
      setBoard(board.features, board.workflow_stages);
    }
  }, [board, setBoard]);

  const features = board?.features ?? [];
  const stages = board?.workflow_stages ?? [];
  const enabledStages = useMemo(() => stages.filter((s) => s.enabled), [stages]);

  const onDragEnd = useCallback(
    (result: DropResult) => {
      if (!result.destination) return;

      const sourceDroppable = result.source.droppableId;
      const destDroppable = result.destination.droppableId;

      if (sourceDroppable === destDroppable) return;

      // droppableId format: "featureId::stageId"
      const [, destStageId] = destDroppable.split('::');
      const [sourceFeatureId] = sourceDroppable.split('::');
      const taskId = result.draggableId;

      if (destStageId && sourceFeatureId && taskId) {
        moveTask.mutate({
          featureId: sourceFeatureId,
          taskId,
          data: { target_stage_id: destStageId },
        });
      }
    },
    [moveTask],
  );

  if (isLoading) return <Spin size="large" style={{ display: 'block', margin: '60px auto' }} />;

  if (features.length === 0) {
    return (
      <Empty description="No features yet" style={{ marginTop: 60 }}>
        <Text type="secondary">Create a new feature to get started.</Text>
      </Empty>
    );
  }

  return (
    <DragDropContext onDragEnd={onDragEnd}>
      {/* Stage column headers — sticky so they stay visible while scrolling */}
      <div
        style={{
          display: 'flex',
          gap: 8,
          paddingLeft: 168,
          marginBottom: 4,
          position: 'sticky',
          top: 0,
          zIndex: 1,
          background: '#fff',
        }}
      >
        {enabledStages.map((stage) => (
          <div
            key={stage.id}
            className="pct-col-header"
            style={{
              minWidth: 180,
              maxWidth: 220,
              flex: '1 0 180px',
              textAlign: 'center',
              padding: '4px 0',
              borderBottom: '2px solid var(--pct-color-primary)',
            }}
          >
            {stage.label}
          </div>
        ))}
      </div>

      {/* Swimlanes */}
      {features.map((feature) => (
        <Swimlane key={feature.id} feature={feature} stages={stages} />
      ))}
    </DragDropContext>
  );
}
