import { useCallback, useEffect } from 'react';
import { DragDropContext, type DropResult } from '@hello-pangea/dnd';
import { Spin, Empty, Typography } from 'antd';
import Swimlane from './Swimlane';
import { useBoardQuery } from '../../hooks/useBoardQueries';
import { useBoardStore } from '../../stores/boardStore';

const { Text } = Typography;

export default function KanbanBoard() {
  const { data: board, isLoading } = useBoardQuery();
  const setBoard = useBoardStore((s) => s.setBoard);

  // Keep store in sync with query data
  useEffect(() => {
    if (board) {
      setBoard(board.features, board.workflow_stages);
    }
  }, [board, setBoard]);

  const features = board?.features ?? [];
  const stages = board?.workflow_stages ?? [];
  const enabledStages = stages.filter((s) => s.enabled);

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
        // Fire the mutation -- useMoveTask requires featureId/taskId at call site
        // We use the board API directly here for simplicity
        import('../../api/boardApi').then(({ boardApi }) => {
          boardApi.moveTask(sourceFeatureId, taskId, { target_stage_id: destStageId });
        });
      }
    },
    [],
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
            style={{
              minWidth: 180,
              maxWidth: 220,
              flex: '1 0 180px',
              textAlign: 'center',
              fontWeight: 600,
              fontSize: 12,
              color: '#595959',
              textTransform: 'uppercase',
              padding: '4px 0',
              borderBottom: '2px solid #1890ff',
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
