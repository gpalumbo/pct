import { Card, Tag, Typography } from 'antd';
import { Draggable } from '@hello-pangea/dnd';
import type { Task } from '../../types/board';

const { Text } = Typography;

const AGENT_COLORS: Record<string, string> = {
  llm: '#1890ff',
  user: '#52c41a',
  tool: '#faad14',
};

interface TaskCardProps {
  task: Task;
  index: number;
  featureId: string;
}

export default function TaskCard({ task, index, featureId }: TaskCardProps) {
  const isBlocked = task.depends_on.length > 0 || task.cross_depends_on.length > 0;
  const borderColor = task.agent ? (AGENT_COLORS[task.agent] || '#d9d9d9') : '#d9d9d9';

  return (
    <Draggable draggableId={`${featureId}:${task.id}`} index={index}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          style={{
            marginBottom: 4,
            ...provided.draggableProps.style,
          }}
        >
          <Card
            size="small"
            style={{
              borderLeft: `3px solid ${borderColor}`,
              opacity: isBlocked ? 0.6 : 1,
              background: snapshot.isDragging ? '#e6f7ff' : undefined,
            }}
            bodyStyle={{ padding: '6px 8px' }}
          >
            <Text
              ellipsis={{ tooltip: task.title }}
              style={{ fontSize: 12, display: 'block', marginBottom: 2 }}
            >
              {task.title}
            </Text>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {task.agent && (
                <Tag color={AGENT_COLORS[task.agent] || 'default'} style={{ fontSize: 10, margin: 0, lineHeight: '16px' }}>
                  {task.agent}
                </Tag>
              )}
              {isBlocked && (
                <Tag color="red" style={{ fontSize: 10, margin: 0, lineHeight: '16px' }}>
                  blocked
                </Tag>
              )}
            </div>
          </Card>
        </div>
      )}
    </Draggable>
  );
}
