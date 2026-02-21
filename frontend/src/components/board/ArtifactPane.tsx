import { useEffect, useState } from 'react';
import { Button, Input, Spin, message } from 'antd';
import { SaveOutlined, ReloadOutlined, EditOutlined } from '@ant-design/icons';
import { useArtifact, useSaveArtifact, useUpdateTask } from '../../hooks/useBoardQueries';
import ArtifactEditorModal from './ArtifactEditorModal';
import './sidebar.css';

interface ArtifactPaneProps {
  featureId: string;
  taskId: string;
}

export default function ArtifactPane({ featureId, taskId }: ArtifactPaneProps) {
  const { data: artifact, isLoading, refetch } = useArtifact(featureId, taskId);
  const saveMutation = useSaveArtifact();
  const updateTask = useUpdateTask();
  const [content, setContent] = useState('');
  const [dirty, setDirty] = useState(false);
  const [path, setPath] = useState('');
  const [editorOpen, setEditorOpen] = useState(false);

  useEffect(() => {
    if (artifact) {
      setContent(artifact.content);
      setPath(artifact.path);
      setDirty(false);
    }
  }, [artifact]);

  const handlePathSave = () => {
    const trimmed = path.trim();
    if (trimmed === (artifact?.path || '')) return;
    updateTask.mutate(
      { featureId, taskId, data: { artifact_path: trimmed } },
      {
        onSuccess: () => {
          refetch();
          message.success('Artifact path updated');
        },
        onError: () => message.error('Failed to update artifact path'),
      },
    );
  };

  const handleSave = () => {
    saveMutation.mutate(
      { featureId, taskId, content },
      {
        onSuccess: () => {
          setDirty(false);
          message.success('Artifact saved');
        },
        onError: () => {
          message.error('Failed to save artifact');
        },
      },
    );
  };

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 24 }}>
        <Spin size="small" />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '8px 12px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexShrink: 0 }}>
        <Input
          size="small"
          value={path}
          onChange={(e) => setPath(e.target.value)}
          onBlur={handlePathSave}
          onPressEnter={handlePathSave}
          placeholder="artifacts/feature/task.md"
          style={{ flex: 1, fontSize: 11, fontFamily: 'monospace' }}
        />
        <Button
          size="small"
          icon={<EditOutlined />}
          onClick={() => setEditorOpen(true)}
        />
        <Button
          size="small"
          icon={<ReloadOutlined />}
          onClick={() => refetch()}
        />
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
      <Input.TextArea
        value={content}
        onChange={(e) => {
          setContent(e.target.value);
          setDirty(true);
        }}
        style={{ flex: 1, fontFamily: 'monospace', fontSize: 12, resize: 'none' }}
        placeholder={artifact?.exists ? '' : 'Artifact file does not exist yet. Type content and save to create it.'}
      />
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
