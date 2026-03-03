import { useEffect, useState } from 'react';
import { Button, Spin, Typography, message } from 'antd';
import {
  EditOutlined,
  ReloadOutlined,
  SaveOutlined,
  UpOutlined,
  DownOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import { useArtifact, useSaveArtifact } from '../../hooks/useBoardQueries';
import type { AgentType } from '../../types/enums';
import ArtifactEditorModal from './ArtifactEditorModal';
import './sidebar.css';

const { Text } = Typography;

/* ------------------------------------------------------------------ */
/*  Sub-component: Text Preview                                        */
/* ------------------------------------------------------------------ */

interface TextPreviewProps {
  featureId: string;
  taskId: string;
}

function TextPreview({ featureId, taskId }: TextPreviewProps) {
  const { data: artifact, isLoading, refetch } = useArtifact(featureId, taskId);
  const saveMutation = useSaveArtifact();
  const [content, setContent] = useState('');
  const [dirty, setDirty] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    if (artifact) {
      setContent(artifact.content);
      setDirty(false);
    }
  }, [artifact]);

  const handleSave = () => {
    saveMutation.mutate(
      { featureId, taskId, content },
      {
        onSuccess: () => {
          setDirty(false);
          message.success('Artifact saved');
        },
        onError: () => message.error('Failed to save artifact'),
      },
    );
  };

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 12 }}>
        <Spin size="small" />
      </div>
    );
  }

  return (
    <div className="artifact-output-text-section">
      {/* Toolbar */}
      <div className="artifact-output-section-header" onClick={() => setCollapsed(!collapsed)}>
        <Text
          type="secondary"
          style={{ fontSize: 11, fontWeight: 500, flex: 1, cursor: 'pointer' }}
        >
          {collapsed ? (
            <DownOutlined style={{ fontSize: 9, marginRight: 4 }} />
          ) : (
            <UpOutlined style={{ fontSize: 9, marginRight: 4 }} />
          )}
          Text Artifact
        </Text>
        <div onClick={(e) => e.stopPropagation()} style={{ display: 'flex', gap: 4 }}>
          <Button size="small" icon={<EditOutlined />} onClick={() => setEditorOpen(true)} />
          <Button size="small" icon={<ReloadOutlined />} onClick={() => refetch()} />
          <Button
            size="small"
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            disabled={!dirty}
            loading={saveMutation.isPending}
          >
            Save
          </Button>
        </div>
      </div>

      {!collapsed && (
        <div className="artifact-output-text-body">
          {content ? (
            <ReactMarkdown>{content}</ReactMarkdown>
          ) : (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {artifact
                ? '(empty)'
                : 'Artifact file does not exist yet. Use "Copy to artifact" or the editor to create it.'}
            </Text>
          )}
        </div>
      )}

      <ArtifactEditorModal
        open={editorOpen}
        content={content}
        onSave={(md) => {
          setContent(md);
          setDirty(true);
          setEditorOpen(false);
        }}
        onCancel={() => setEditorOpen(false)}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Sub-component: Image Section                                       */
/* ------------------------------------------------------------------ */

interface ImageSectionProps {
  activeAgentType: AgentType | null;
}

function ImageSection({ activeAgentType }: ImageSectionProps) {
  const [collapsed, setCollapsed] = useState(false);
  const showSection = activeAgentType === 'image_gen';

  if (!showSection) return null;

  return (
    <div className="artifact-output-image-section">
      <div className="artifact-output-section-header" onClick={() => setCollapsed(!collapsed)}>
        <Text
          type="secondary"
          style={{ fontSize: 11, fontWeight: 500, flex: 1, cursor: 'pointer' }}
        >
          {collapsed ? (
            <DownOutlined style={{ fontSize: 9, marginRight: 4 }} />
          ) : (
            <UpOutlined style={{ fontSize: 9, marginRight: 4 }} />
          )}
          Images
        </Text>
      </div>

      {!collapsed && (
        <div style={{ padding: '8px', minHeight: 60 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Image generation is available. Send a prompt to generate images.
          </Text>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main: ArtifactOutputPane                                           */
/* ------------------------------------------------------------------ */

interface ArtifactOutputPaneProps {
  featureId: string;
  taskId: string;
  activeAgentType: AgentType | null;
  pendingImagePrompt: string | null;
  onPromptConsumed: () => void;
}

export default function ArtifactOutputPane({
  featureId,
  taskId,
  activeAgentType,
}: ArtifactOutputPaneProps) {
  return (
    <div className="artifact-output-pane">
      <TextPreview featureId={featureId} taskId={taskId} />
      <ImageSection activeAgentType={activeAgentType} />
    </div>
  );
}
