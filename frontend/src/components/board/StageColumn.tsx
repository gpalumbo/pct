import { Droppable } from '@hello-pangea/dnd';
import TaskCard from './TaskCard';
import type { Task, WorkflowStage } from '../../types/board';

interface StageColumnProps {
  stage: WorkflowStage;
  tasks: Task[];
  featureId: string;
}

export default function StageColumn({ stage, tasks, featureId }: StageColumnProps) {
  const droppableId = `${featureId}::${stage.id}`;

  return (
    <div
      style={{
        minWidth: 180,
        maxWidth: 220,
        flex: '1 0 180px',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Droppable droppableId={droppableId}>
        {(provided, snapshot) => (
          <div
            ref={provided.innerRef}
            {...provided.droppableProps}
            style={{
              flex: 1,
              minHeight: 60,
              padding: 4,
              borderRadius: 4,
              backgroundColor: snapshot.isDraggingOver ? '#e6f7ff' : '#fafafa',
              transition: 'background-color 0.2s',
            }}
          >
            {tasks.map((task, idx) => (
              <TaskCard
                key={task.id}
                task={task}
                index={idx}
                featureId={featureId}
              />
            ))}
            {provided.placeholder}
          </div>
        )}
      </Droppable>
    </div>
  );
}
