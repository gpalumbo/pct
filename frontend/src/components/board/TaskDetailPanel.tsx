import { Drawer, Typography, Descriptions, Tag, Button, Select, Space, Divider } from 'antd';
import { CloseOutlined } from '@ant-design/icons';
import { useBoardStore } from '../../stores/boardStore';
import { useUIStore } from '../../stores/uiStore';
import { useMoveTask } from '../../hooks/useBoardQueries';
import ArtifactPane from './ArtifactPane';
import PlanningChat from '../chat/PlanningChat';
import type { Task, WorkflowStage } from '../../types/board';

const { Title, Text } = Typography;

interface TaskDetailPanelProps {
  task: Task | null;
  featureId: string | null;
  stages: WorkflowStage[];
}

export default function TaskDetailPanel({ task, featureId, stages }: TaskDetailPanelProps) {
  const { taskPanelOpen, setTaskPanelOpen, taskPanelWidth } = useUIStore();
  const selectTask = useBoardStore((s) => s.selectTask);
  const moveTask = useMoveTask(featureId ?? '', task?.id ?? '');

  const currentStage = stages.find((s) => s.id === task?.current_stage_id);
  const enabledStages = stages.filter((s) => s.enabled);

  const handleStageChange = async (stageId: string) => {
    if (!task || !featureId) return;
    await moveTask.mutateAsync({ target_stage_id: stageId });
  };

  const handleClose = () => {
    setTaskPanelOpen(false);
    selectTask(null, null);
  };

  return (
    <Drawer
      open={taskPanelOpen && !!task}
      onClose={handleClose}
      width={taskPanelWidth}
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={5} style={{ margin: 0 }}>
            Task Details
          </Title>
          <Button type="text" icon={<CloseOutlined />} onClick={handleClose} />
        </div>
      }
      closable={false}
    >
      {task && (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 16 }}>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="Title">
              <Text strong>{task.title}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="Stage">
              <Tag color="blue">{currentStage?.label ?? task.current_stage_id}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag
                color={
                  task.execution_status === 'running'
                    ? 'processing'
                    : task.execution_status === 'error'
                      ? 'error'
                      : 'default'
                }
              >
                {task.execution_status}
              </Tag>
            </Descriptions.Item>
            {task.blocked_by.length > 0 && (
              <Descriptions.Item label="Blocked By">
                {task.blocked_by.map((id) => (
                  <Tag key={id} color="red">
                    {id}
                  </Tag>
                ))}
              </Descriptions.Item>
            )}
          </Descriptions>

          <Space>
            <Text>Move to:</Text>
            <Select
              value={task.current_stage_id}
              onChange={handleStageChange}
              style={{ width: 200 }}
              loading={moveTask.isPending}
            >
              {enabledStages.map((s) => (
                <Select.Option key={s.id} value={s.id}>
                  {s.label}
                </Select.Option>
              ))}
            </Select>
          </Space>

          <Divider style={{ margin: '8px 0' }} />

          <div style={{ flex: 1, overflow: 'auto' }}>
            <ArtifactPane featureId={featureId!} taskId={task.id} />
          </div>

          <Divider style={{ margin: '8px 0' }} />

          <div style={{ flex: 1, minHeight: 200, overflow: 'auto' }}>
            <PlanningChat sessionId={`${featureId}::${task.id}`} />
          </div>
        </div>
      )}
    </Drawer>
  );
}
