import { useCallback, useRef, useState } from 'react';
import { Modal, Button, Typography, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useCreateTask } from '../../hooks/useBoardQueries';

const { Text } = Typography;

interface AnalysisModalProps {
  open: boolean;
  title: string;
  featureId: string;
  runAnalysis: (
    featureId: string,
    onToken: (token: string) => void,
    onDone: (content: string) => void,
    onError: (error: string) => void,
  ) => AbortController;
  onClose: () => void;
}

interface ParsedTask {
  title: string;
  feature: string;
  type: string;
  reason: string;
}

function parseTaskLines(content: string): ParsedTask[] {
  const tasks: ParsedTask[] = [];
  const regex = /TASK:\s*(.+?)\s*\|\s*FEATURE:\s*(.+?)\s*\|\s*TYPE:\s*(.+?)\s*\|\s*REASON:\s*(.+)/g;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(content)) !== null) {
    tasks.push({
      title: match[1].trim(),
      feature: match[2].trim(),
      type: match[3].trim(),
      reason: match[4].trim(),
    });
  }
  return tasks;
}

export default function AnalysisModal({
  open,
  title,
  featureId,
  runAnalysis,
  onClose,
}: AnalysisModalProps) {
  const [content, setContent] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [done, setDone] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);
  const createTask = useCreateTask();

  const handleStart = useCallback(() => {
    setContent('');
    setStreaming(true);
    setDone(false);

    const controller = runAnalysis(
      featureId,
      (token) => setContent((prev) => prev + token),
      () => {
        setStreaming(false);
        setDone(true);
      },
      (error) => {
        setStreaming(false);
        message.error(error);
      },
    );
    controllerRef.current = controller;
  }, [featureId, runAnalysis]);

  const handleClose = () => {
    if (controllerRef.current) {
      controllerRef.current.abort();
      controllerRef.current = null;
    }
    setContent('');
    setStreaming(false);
    setDone(false);
    onClose();
  };

  const handleCreateTask = (parsed: ParsedTask) => {
    createTask.mutate(
      {
        featureId: parsed.feature,
        data: {
          title: parsed.title,
          artifact_type: parsed.type,
        },
      },
      {
        onSuccess: () => message.success(`Task "${parsed.title}" created`),
        onError: () => message.error(`Failed to create task`),
      },
    );
  };

  const parsedTasks = done ? parseTaskLines(content) : [];

  return (
    <Modal
      title={title}
      open={open}
      onCancel={handleClose}
      width={640}
      footer={[
        <Button key="close" onClick={handleClose}>
          Close
        </Button>,
        !streaming && !done && (
          <Button key="run" type="primary" onClick={handleStart}>
            Run Analysis
          </Button>
        ),
      ]}
    >
      {!content && !streaming && (
        <Text type="secondary">
          Click "Run Analysis" to start. This will analyze all world artifacts for the selected feature.
        </Text>
      )}

      {(content || streaming) && (
        <div
          style={{
            maxHeight: 400,
            overflow: 'auto',
            padding: '8px 12px',
            background: '#fafafa',
            borderRadius: 4,
            fontFamily: 'monospace',
            fontSize: 12,
            whiteSpace: 'pre-wrap',
            marginBottom: 12,
          }}
        >
          {content}
          {streaming && <span className="analysis-cursor">|</span>}
        </div>
      )}

      {done && parsedTasks.length > 0 && (
        <div>
          <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 8 }}>
            Suggested Tasks
          </Text>
          {parsedTasks.map((t, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '4px 0',
                borderBottom: '1px solid #f0f0f0',
              }}
            >
              <div style={{ flex: 1 }}>
                <Text style={{ fontSize: 12 }}>{t.title}</Text>
                <br />
                <Text type="secondary" style={{ fontSize: 10 }}>
                  {t.feature} / {t.type} — {t.reason}
                </Text>
              </div>
              <Button
                size="small"
                icon={<PlusOutlined />}
                onClick={() => handleCreateTask(t)}
              >
                Create
              </Button>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}
