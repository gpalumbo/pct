import { memo, useCallback } from 'react';
import { Card, Typography, Tag } from 'antd';
import { Draggable } from '@hello-pangea/dnd';
import { useBoardStore } from '../../stores/boardStore';
import { useUIStore } from '../../stores/uiStore';
import type { Task } from '../../types/board';
import type { AgentType } from '../../types/enums';

const { Text } = Typography;

const agentBorderColors: Record<AgentType, string> = {
  llm: '#1890ff',
  user: '#52c41a',
  tool: '#faad14',
  image_gen: '#eb2f96',
};

interface TaskCardProps {
  task: Task;
  index: number;
  featureId: string;
  agentType?: AgentType;
}

function TaskCardInner({ task, index, featureId, agentType }: TaskCardProps) {
  const selectTask = useBoardStore((s) => s.selectTask);
  const setTaskPanelOpen = useUIStore((s) => s.setTaskPanelOpen);
  const isBlocked = task.blocked_by.length > 0;
  const borderColor = agentType ? agentBorderColors[agentType] : '#d9d9d9';

  const handleClick = useCallback(() => {
    selectTask(featureId, task.id);
    setTaskPanelOpen(true);
  }, [selectTask, setTaskPanelOpen, featureId, task.id]);

  return (
    <Draggable draggableId={task.id} index={index}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          style={{
            marginBottom: 6,
            opacity: isBlocked ? 0.5 : 1,
            ...provided.draggableProps.style,
          }}
        >
          <Card
            size="small"
            style={{
              borderLeft: `3px solid ${borderColor}`,
              cursor: 'pointer',
              boxShadow: snapshot.isDragging ? '0 4px 12px rgba(0,0,0,0.15)' : undefined,
            }}
            onClick={handleClick}
          >
            <Text strong ellipsis style={{ fontSize: 12 }}>
              {task.title}
            </Text>
            <div style={{ marginTop: 4 }}>
              {task.execution_status !== 'idle' && (
                <Tag
                  color={
                    task.execution_status === 'running'
                      ? 'processing'
                      : task.execution_status === 'error'
                        ? 'error'
                        : 'default'
                  }
                  style={{ fontSize: 10 }}
                >
                  {task.execution_status}
                </Tag>
              )}
              {isBlocked && (
                <Tag color="red" style={{ fontSize: 10 }}>
                  Blocked
                </Tag>
              )}
              {task.is_bypassed && (
                <Tag color="orange" style={{ fontSize: 10 }}>
                  Bypassed
                </Tag>
              )}
            </div>
          </Card>
        </div>
      )}
    </Draggable>
  );
}

const TaskCard = memo(TaskCardInner);
export default TaskCard;
