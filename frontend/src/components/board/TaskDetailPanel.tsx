import { useMemo, useState } from 'react';
import { Button, Select, Tag, Typography, message } from 'antd';
import { CloseOutlined, LinkOutlined } from '@ant-design/icons';
import type { SelectedTask } from '../../stores/boardStore';
import { useBoard, useUpdateTask } from '../../hooks/useBoardQueries';
import { useArtifactTypes } from '../../hooks/useConfigQueries';
import PlanningChat from '../chat/PlanningChat';
import ArtifactPane from './ArtifactPane';
import ImageGenPane from './ImageGenPane';
import CrossRefPicker from './CrossRefPicker';
import './sidebar.css';

const { Text } = Typography;

interface TaskDetailPanelProps {
  selectedTask: SelectedTask;
  onClose: () => void;
}

export default function TaskDetailPanel({ selectedTask, onClose }: TaskDetailPanelProps) {
  const { featureId, taskId, task } = selectedTask;
  const sessionId = `task-${featureId}-${taskId}`;
  const [refPickerOpen, setRefPickerOpen] = useState(false);
  const { data: board } = useBoard();
  const updateTask = useUpdateTask();
  const { data: artifactTypes = [] } = useArtifactTypes();

  const artifactTypeOptions = useMemo(
    () => artifactTypes.map((t) => ({ value: t.id, label: t.label })),
    [artifactTypes],
  );

  const handleRemoveRef = (ref: string) => {
    const newRefs = task.cross_depends_on.filter((r) => r !== ref);
    updateTask.mutate(
      { featureId, taskId, data: { cross_depends_on: newRefs } },
      {
        onError: () => message.error('Failed to update references'),
      },
    );
  };

  const handleRefsSelected = (refs: string[]) => {
    updateTask.mutate(
      { featureId, taskId, data: { cross_depends_on: refs } },
      {
        onSuccess: () => {
          setRefPickerOpen(false);
          message.success('References updated');
        },
        onError: () => message.error('Failed to update references'),
      },
    );
  };

  const handleArtifactTypeChange = (value: string) => {
    updateTask.mutate(
      { featureId, taskId, data: { artifact_type: value } },
      {
        onError: () => message.error('Failed to update artifact type'),
      },
    );
  };

  return (
    <div
      className="task-sidebar"
      style={{
        width: 480,
        minWidth: 480,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}
    >
      {/* Header */}
      <div
        className="task-sidebar-header"
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '8px 12px',
          gap: 8,
          flexShrink: 0,
        }}
      >
        <Text strong style={{ flex: 1, fontSize: 13 }} ellipsis>
          {task.title}
        </Text>
        <Select
          size="small"
          value={task.artifact_type || 'text'}
          onChange={handleArtifactTypeChange}
          options={artifactTypeOptions}
          style={{ width: 110, fontSize: 11 }}
          popupMatchSelectWidth={false}
        />
        <Text type="secondary" style={{ fontSize: 11, flexShrink: 0 }}>
          {featureId}/{taskId}
        </Text>
        <Button
          type="text"
          size="small"
          icon={<CloseOutlined />}
          onClick={onClose}
        />
      </div>

      {/* Cross-references strip */}
      <div
        style={{
          padding: '4px 12px',
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          flexWrap: 'wrap',
          flexShrink: 0,
        }}
      >
        {task.cross_depends_on.map((ref) => (
          <Tag
            key={ref}
            closable
            onClose={() => handleRemoveRef(ref)}
            style={{ fontSize: 10, margin: 0 }}
          >
            {ref}
          </Tag>
        ))}
        <Button
          size="small"
          type="dashed"
          icon={<LinkOutlined />}
          onClick={() => setRefPickerOpen(true)}
          style={{ fontSize: 11 }}
        >
          Add Ref
        </Button>
        <Text type="secondary" style={{ fontSize: 10, marginLeft: 'auto' }}>
          Tip: use [[Name]] to auto-link
        </Text>
      </div>

      {/* Chat pane — top half */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <PlanningChat sessionId={sessionId} artifactPath={task.artifact_path} featureId={featureId} taskId={taskId} />
      </div>

      {/* Divider */}
      <div className="task-sidebar-divider" style={{ flexShrink: 0 }} />

      {/* Artifact pane — bottom portion */}
      <div style={{
        height: task.artifact_type === 'image' ? 480 : 240,
        minHeight: 200,
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
      }}>
        <div className="task-sidebar-section-label" style={{ padding: '4px 12px' }}>
          <Text type="secondary" style={{ fontSize: 11 }}>
            {task.artifact_type === 'image' ? 'Image Studio' : 'Artifact'}
          </Text>
        </div>
        <div style={{ flex: 1, minHeight: 0 }}>
          {task.artifact_type === 'image' ? (
            <ImageGenPane featureId={featureId} taskId={taskId} taskTitle={task.title} />
          ) : (
            <ArtifactPane featureId={featureId} taskId={taskId} taskTitle={task.title} />
          )}
        </div>
      </div>

      {/* Cross-reference picker modal */}
      <CrossRefPicker
        open={refPickerOpen}
        features={board?.features || []}
        currentFeatureId={featureId}
        currentTaskId={taskId}
        selected={task.cross_depends_on}
        onOk={handleRefsSelected}
        onCancel={() => setRefPickerOpen(false)}
      />
    </div>
  );
}
