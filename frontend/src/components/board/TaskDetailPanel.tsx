import { useCallback, useMemo, useRef, useState } from 'react';
import { Button, Select, Tag, Typography } from 'antd';
import { CloseOutlined } from '@ant-design/icons';
import { useBoardStore } from '../../stores/boardStore';
import { useUIStore } from '../../stores/uiStore';
import { useMoveTask } from '../../hooks/useBoardQueries';
import usePlanningChat from '../../hooks/usePlanningChat';
import type { RefineTarget } from '../chat/ChatInput';
import type { AgentType } from '../../types/enums';
import type { Task, WorkflowStage } from '../../types/board';
import MessageList from '../chat/MessageList';
import ChatInput from '../chat/ChatInput';
import ArtifactOutputPane from './ArtifactOutputPane';
import './sidebar.css';

const { Text } = Typography;

const MIN_WIDTH = 500;
const MAX_WIDTH = 900;

interface TaskDetailPanelProps {
  task: Task | null;
  featureId: string | null;
  stages: WorkflowStage[];
}

export default function TaskDetailPanel({ task, featureId, stages }: TaskDetailPanelProps) {
  const { taskPanelOpen, setTaskPanelOpen, taskPanelWidth, setTaskPanelWidth } = useUIStore();
  const selectTask = useBoardStore((s) => s.selectTask);
  const moveTask = useMoveTask(featureId ?? '', task?.id ?? '');
  const sessionId = task && featureId ? `task-${featureId}-${task.id}` : undefined;

  /* ------------------------------------------------------------------ */
  /*  Resizable sidebar                                                  */
  /* ------------------------------------------------------------------ */
  const [isResizing, setIsResizing] = useState(false);
  const resizeRef = useRef<{ startX: number; startWidth: number } | null>(null);

  const handleResizeStart = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      resizeRef.current = { startX: e.clientX, startWidth: taskPanelWidth };
      setIsResizing(true);

      const onMouseMove = (ev: MouseEvent) => {
        if (!resizeRef.current) return;
        const delta = resizeRef.current.startX - ev.clientX;
        const newWidth = Math.max(
          MIN_WIDTH,
          Math.min(MAX_WIDTH, resizeRef.current.startWidth + delta),
        );
        setTaskPanelWidth(newWidth);
      };

      const onMouseUp = () => {
        setIsResizing(false);
        resizeRef.current = null;
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
      };

      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
    },
    [taskPanelWidth, setTaskPanelWidth],
  );

  /* ------------------------------------------------------------------ */
  /*  Agent type + imagegen routing                                      */
  /* ------------------------------------------------------------------ */
  const [activeAgentType, setActiveAgentType] = useState<AgentType | null>(null);
  const [pendingImagePrompt, setPendingImagePrompt] = useState<string | null>(null);

  /* ------------------------------------------------------------------ */
  /*  Refine image -> input                                               */
  /* ------------------------------------------------------------------ */
  const [refineTarget, setRefineTarget] = useState<RefineTarget | null>(null);

  const handleCancelRefine = useCallback(() => {
    setRefineTarget(null);
  }, []);

  /* ------------------------------------------------------------------ */
  /*  Chat hook                                                          */
  /* ------------------------------------------------------------------ */
  const chat = usePlanningChat({
    sessionId,
    featureId: featureId ?? undefined,
    taskId: task?.id,
    taskStage: task?.current_stage_id,
    onAgentTypeChange: setActiveAgentType,
    onImageGenerate: setPendingImagePrompt,
  });

  // Wrap handleSend to clear refine target on send
  const handleSend = useCallback(
    (content: string, agentId: string | null) => {
      chat.handleSend(content, agentId);
      if (refineTarget) {
        setRefineTarget(null);
      }
    },
    [chat, refineTarget],
  );

  /* ------------------------------------------------------------------ */
  /*  Config UI                                                          */
  /* ------------------------------------------------------------------ */
  const enabledStages = useMemo(() => stages.filter((s) => s.enabled), [stages]);
  const currentStage = useMemo(
    () => stages.find((s) => s.id === task?.current_stage_id),
    [stages, task?.current_stage_id],
  );

  const handleStageChange = async (stageId: string) => {
    if (!task || !featureId) return;
    await moveTask.mutateAsync({ target_stage_id: stageId });
  };

  const handleClose = () => {
    setTaskPanelOpen(false);
    selectTask(null, null);
  };

  if (!taskPanelOpen || !task || !featureId) return null;

  return (
    <div
      className="task-sidebar"
      style={{
        width: taskPanelWidth,
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
          value={task.current_stage_id}
          onChange={handleStageChange}
          loading={moveTask.isPending}
          style={{ width: 130, fontSize: 11 }}
          popupMatchSelectWidth={false}
        >
          {enabledStages.map((s) => (
            <Select.Option key={s.id} value={s.id}>
              {s.label}
            </Select.Option>
          ))}
        </Select>
        <Tag color={currentStage ? 'blue' : 'default'} style={{ fontSize: 10, margin: 0 }}>
          {currentStage?.label ?? task.current_stage_id}
        </Tag>
        <Text type="secondary" style={{ fontSize: 11, flexShrink: 0 }}>
          {featureId}/{task.id}
        </Text>
        <Button type="text" size="small" icon={<CloseOutlined />} onClick={handleClose} />
      </div>

      {/* Cross-references & blocked_by strip */}
      {(task.blocked_by.length > 0 || task.cross_refs.length > 0) && (
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
          {task.blocked_by.map((ref) => (
            <Tag key={ref} color="red" style={{ fontSize: 10, margin: 0 }}>
              blocked: {ref}
            </Tag>
          ))}
          {task.cross_refs.map((ref) => (
            <Tag key={ref} color="blue" style={{ fontSize: 10, margin: 0 }}>
              {ref}
            </Tag>
          ))}
        </div>
      )}

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
            sessionId={chat.activeSessionId || ''}
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
        taskStage={task.current_stage_id}
        refineTarget={refineTarget}
        onCancelRefine={handleCancelRefine}
      />

      {/* ============================================================ */}
      {/* SECTION 3: Artifact / Output (split view)                     */}
      {/* ============================================================ */}
      <div className="task-sidebar-divider" style={{ flexShrink: 0 }} />
      <div
        style={{
          height: '40%',
          minHeight: 200,
          flexShrink: 0,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <ArtifactOutputPane
          featureId={featureId}
          taskId={task.id}
          activeAgentType={activeAgentType}
          pendingImagePrompt={pendingImagePrompt}
          onPromptConsumed={() => setPendingImagePrompt(null)}
        />
      </div>
    </div>
  );
}
