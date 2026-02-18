import { Button, Typography } from 'antd';
import { CloseOutlined } from '@ant-design/icons';
import type { SelectedTask } from '../../stores/boardStore';
import TaskChat from './TaskChat';
import ArtifactPane from './ArtifactPane';

const { Text } = Typography;

interface TaskDetailPanelProps {
  selectedTask: SelectedTask;
  onClose: () => void;
}

export default function TaskDetailPanel({ selectedTask, onClose }: TaskDetailPanelProps) {
  const { featureId, taskId, task } = selectedTask;
  const sessionId = `task-${featureId}-${taskId}`;

  return (
    <div
      style={{
        width: 480,
        minWidth: 480,
        borderLeft: '1px solid #e8e8e8',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: '#fff',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '8px 12px',
          borderBottom: '1px solid #f0f0f0',
          gap: 8,
          flexShrink: 0,
        }}
      >
        <Text strong style={{ flex: 1, fontSize: 13 }} ellipsis>
          {task.title}
        </Text>
        <Text style={{ fontSize: 11, flexShrink: 0, color: '#333' }}>
          {featureId}/{taskId}
        </Text>
        <Button
          type="text"
          size="small"
          icon={<CloseOutlined />}
          onClick={onClose}
        />
      </div>

      {/* Chat pane — top half */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <TaskChat sessionId={sessionId} artifactPath={task.artifact_path} />
      </div>

      {/* Divider */}
      <div style={{ borderTop: '1px solid #e8e8e8', flexShrink: 0 }} />

      {/* Artifact pane — bottom portion */}
      <div style={{ height: 240, minHeight: 200, display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
        <div style={{ padding: '4px 12px', borderBottom: '1px solid #f0f0f0' }}>
          <Text style={{ fontSize: 11, color: '#333' }}>Artifact</Text>
        </div>
        <div style={{ flex: 1, minHeight: 0 }}>
          <ArtifactPane featureId={featureId} taskId={taskId} />
        </div>
      </div>
    </div>
  );
}
