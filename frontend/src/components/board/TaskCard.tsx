import { Card, Tag, Typography } from 'antd';
import { Draggable } from '@hello-pangea/dnd';
import type { Task } from '../../types/board';
import { useBoardStore } from '../../stores/boardStore';

const { Text } = Typography;

const AGENT_COLORS: Record<string, string> = {
  llm: '#1890ff',
  user: '#52c41a',
  tool: '#faad14',
};

const ARTIFACT_TYPE_COLORS: Record<string, string> = {
  timeline: '#13c2c2',
  location: '#52c41a',
  character: '#1890ff',
  faction: '#722ed1',
  'magic-system': '#eb2f96',
  technology: '#fa8c16',
  item: '#faad14',
  'story-arc': '#2f54eb',
  chapter: '#597ef7',
};

interface TaskCardProps {
  task: Task;
  index: number;
  featureId: string;
}

export default function TaskCard({ task, index, featureId }: TaskCardProps) {
  const isBlocked = task.depends_on.length > 0 || task.cross_depends_on.length > 0;
  const borderColor = task.agent ? AGENT_COLORS[task.agent] || '#d9d9d9' : '#d9d9d9';
  const setSelectedTask = useBoardStore((s) => s.setSelectedTask);
  const selectedTask = useBoardStore((s) => s.selectedTask);
  const isSelected = selectedTask?.taskId === task.id && selectedTask?.featureId === featureId;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedTask({ featureId, taskId: task.id, task });
  };

  return (
    <Draggable draggableId={`${featureId}:${task.id}`} index={index}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          onClick={handleClick}
          style={{
            marginBottom: 4,
            cursor: 'pointer',
            ...provided.draggableProps.style,
          }}
        >
          <Card
            size="small"
            style={{
              borderLeft: `3px solid ${borderColor}`,
              opacity: isBlocked ? 0.6 : 1,
              background: snapshot.isDragging ? '#e6f7ff' : isSelected ? '#e6f7ff' : undefined,
            }}
            bodyStyle={{ padding: '6px 8px' }}
          >
            <Text
              ellipsis={{ tooltip: task.title }}
              style={{ fontSize: 12, display: 'block', marginBottom: 2 }}
            >
              {task.title}
            </Text>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
              {task.artifact_type && task.artifact_type !== 'text' && (
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: ARTIFACT_TYPE_COLORS[task.artifact_type] || '#d9d9d9',
                    display: 'inline-block',
                    flexShrink: 0,
                  }}
                  title={task.artifact_type}
                />
              )}
              {task.agent && (
                <Tag
                  color={AGENT_COLORS[task.agent] || 'default'}
                  style={{ fontSize: 10, margin: 0, lineHeight: '16px' }}
                >
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
