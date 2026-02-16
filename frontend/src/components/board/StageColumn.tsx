import { Droppable } from '@hello-pangea/dnd';
import type { Task } from '../../types/board';
import TaskCard from './TaskCard';

interface StageColumnProps {
  featureId: string;
  stage: string;
  tasks: Task[];
}

export default function StageColumn({ featureId, stage, tasks }: StageColumnProps) {
  const droppableId = `${featureId}:${stage}`;

  return (
    <Droppable droppableId={droppableId}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.droppableProps}
          style={{
            minHeight: 40,
            padding: 4,
            background: snapshot.isDraggingOver ? '#f0f5ff' : undefined,
            borderRadius: 4,
            transition: 'background 0.2s',
          }}
        >
          {tasks.map((task, index) => (
            <TaskCard key={task.id} task={task} index={index} featureId={featureId} />
          ))}
          {provided.placeholder}
        </div>
      )}
    </Droppable>
  );
}
