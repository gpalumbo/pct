import { useCallback, useMemo, useRef, useState } from 'react';
import { Button, Select, Tag, Typography, message } from 'antd';
import { CloseOutlined, LinkOutlined } from '@ant-design/icons';
import type { SelectedTask } from '../../stores/boardStore';
import type { AgentType } from '../../types/config';
import type { GeneratedImage } from '../../api/imagegenApi';
import { useBoard, useUpdateTask } from '../../hooks/useBoardQueries';
import { useArtifactTypes, useAgents } from '../../hooks/useConfigQueries';
import usePlanningChat from '../../hooks/usePlanningChat';
import type { RefineTarget } from '../chat/ChatInput';
import MessageList from '../chat/MessageList';
import ChatInput from '../chat/ChatInput';
import ArtifactOutputPane from './ArtifactOutputPane';
import CrossRefPicker from './CrossRefPicker';
import './sidebar.css';

const { Text } = Typography;

const MIN_WIDTH = 500;
const MAX_WIDTH = 900;
const DEFAULT_WIDTH = 520;

interface TaskDetailPanelProps {
  selectedTask: SelectedTask;
  onClose: () => void;
}

export default function TaskDetailPanel({ selectedTask, onClose }: TaskDetailPanelProps) {
  const { featureId, taskId, task } = selectedTask;
  const sessionId = `task-${featureId}-${taskId}`;

  /* ------------------------------------------------------------------ */
  /*  Resizable sidebar                                                  */
  /* ------------------------------------------------------------------ */
  const [width, setWidth] = useState(DEFAULT_WIDTH);
  const [isResizing, setIsResizing] = useState(false);
  const resizeRef = useRef<{ startX: number; startWidth: number } | null>(null);

  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    resizeRef.current = { startX: e.clientX, startWidth: width };
    setIsResizing(true);

    const onMouseMove = (ev: MouseEvent) => {
      if (!resizeRef.current) return;
      // Dragging left edge: moving left increases width
      const delta = resizeRef.current.startX - ev.clientX;
      const newWidth = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, resizeRef.current.startWidth + delta));
      setWidth(newWidth);
    };

    const onMouseUp = () => {
      setIsResizing(false);
      resizeRef.current = null;
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }, [width]);

  /* ------------------------------------------------------------------ */
  /*  Agent type + imagegen routing                                      */
  /* ------------------------------------------------------------------ */
  const [activeAgentType, setActiveAgentType] = useState<AgentType | null>(null);
  const [pendingImagePrompt, setPendingImagePrompt] = useState<string | null>(null);

  /* ------------------------------------------------------------------ */
  /*  Refine image → input                                               */
  /* ------------------------------------------------------------------ */
  const [refineTarget, setRefineTarget] = useState<RefineTarget | null>(null);
  const [refineSourceImage, setRefineSourceImage] = useState<string | null>(null);
  const { data: agents = [] } = useAgents();

  const handleRefineImage = useCallback((img: GeneratedImage) => {
    // Find the blob URL for this image (it should already be loaded)
    // We'll use a proxy URL for the chip display
    const imageUrl = `/api/imagegen/${featureId}/${taskId}/images/${img.filename}`;
    setRefineTarget({ filename: img.filename, imageUrl });
    setRefineSourceImage(img.filename);

    // Auto-switch to imagegen agent
    const imagegenAgent = agents.find(a => a.agent_type === 'imagegen');
    if (imagegenAgent) {
      chat.handleAgentChange(imagegenAgent.id);
    }
  }, [featureId, taskId, agents]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleCancelRefine = useCallback(() => {
    setRefineTarget(null);
    setRefineSourceImage(null);
  }, []);

  /* ------------------------------------------------------------------ */
  /*  Chat hook (shared state for all three sections)                    */
  /* ------------------------------------------------------------------ */
  const chat = usePlanningChat({
    sessionId,
    artifactPath: task.artifact_path,
    featureId,
    taskId,
    taskStage: task.status,
    onAgentTypeChange: setActiveAgentType,
    onImageGenerate: setPendingImagePrompt,
  });

  // Wrap handleSend to clear refine target on send
  const handleSend = useCallback((content: string, agentId: string | null) => {
    chat.handleSend(content, agentId);
    if (refineTarget) {
      setRefineTarget(null);
      // Keep refineSourceImage until prompt is consumed
    }
  }, [chat, refineTarget]);

  /* ------------------------------------------------------------------ */
  /*  Config UI                                                          */
  /* ------------------------------------------------------------------ */
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
      { onError: () => message.error('Failed to update references') },
    );
  };

  const handleRefsSelected = (refs: string[]) => {
    updateTask.mutate(
      { featureId, taskId, data: { cross_depends_on: refs } },
      {
        onSuccess: () => { setRefPickerOpen(false); message.success('References updated'); },
        onError: () => message.error('Failed to update references'),
      },
    );
  };

  const handleArtifactTypeChange = (value: string) => {
    updateTask.mutate(
      { featureId, taskId, data: { artifact_type: value } },
      { onError: () => message.error('Failed to update artifact type') },
    );
  };

  /* ------------------------------------------------------------------ */
  /*  Render                                                             */
  /* ------------------------------------------------------------------ */
  return (
    <div
      className="task-sidebar"
      style={{
        width,
        minWidth: MIN_WIDTH,
        maxWidth: MAX_WIDTH,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}
    >
      {/* Resize handle */}
      <div
        className={`task-sidebar-resize-handle${isResizing ? ' active' : ''}`}
        onMouseDown={handleResizeStart}
      />

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

      {/* ============================================================ */}
      {/* SECTION 1: Context Window (messages)                          */}
      {/* ============================================================ */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        {chat.sessionLoading || chat.messagesLoading ? (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1 }}>
            <Text type="secondary">Loading chat...</Text>
          </div>
        ) : (
          <MessageList
            messages={chat.messages}
            streamingContent={chat.streamingContent}
            isStreaming={chat.isStreaming}
            onUpdateMessage={chat.handleUpdateMessage}
            onDeleteMessage={chat.handleDeleteMessage}
            onReplay={chat.handleReplay}
            onTruncateAndReplay={chat.handleTruncateAndReplay}
            onCopyToArtifact={chat.handleCopyToArtifact}
          />
        )}
      </div>

      {/* ============================================================ */}
      {/* SECTION 2: Input                                              */}
      {/* ============================================================ */}
      <ChatInput
        isStreaming={chat.isStreaming}
        onSend={handleSend}
        onStop={chat.handleStop}
        selectedAgent={chat.selectedAgent}
        onAgentChange={chat.handleAgentChange}
        taskStage={task.status}
        refineTarget={refineTarget}
        onCancelRefine={handleCancelRefine}
      />

      {/* ============================================================ */}
      {/* SECTION 3: Artifact / Output (split view)                     */}
      {/* ============================================================ */}
      <div className="task-sidebar-divider" style={{ flexShrink: 0 }} />
      <div style={{ height: '40%', minHeight: 200, flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
        <ArtifactOutputPane
          featureId={featureId}
          taskId={taskId}
          taskTitle={task.title}
          activeAgentType={activeAgentType}
          pendingImagePrompt={pendingImagePrompt}
          onPromptConsumed={() => { setPendingImagePrompt(null); setRefineSourceImage(null); }}
          refineSourceImage={refineSourceImage}
          onRefineImage={handleRefineImage}
        />
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
