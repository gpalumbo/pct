import { useState } from 'react';
import { Button, Spin, Typography, Empty, App } from 'antd';
import { EditOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import { boardApi } from '../../api/boardApi';
import { useSaveArtifact } from '../../hooks/useBoardQueries';
import ArtifactEditorModal from './ArtifactEditorModal';

const { Title } = Typography;

interface ArtifactPaneProps {
  featureId: string;
  taskId: string;
}

export default function ArtifactPane({ featureId, taskId }: ArtifactPaneProps) {
  const [editorOpen, setEditorOpen] = useState(false);
  const { message } = App.useApp();
  const saveMutation = useSaveArtifact();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['artifact', featureId, taskId],
    queryFn: () => boardApi.getArtifact(featureId, taskId),
    enabled: !!featureId && !!taskId,
  });

  if (isLoading) return <Spin size="small" />;

  const content = data?.content ?? '';

  const handleSave = async (md: string) => {
    try {
      await saveMutation.mutateAsync({ featureId, taskId, content: md });
      message.success('Artifact saved');
      setEditorOpen(false);
      refetch();
    } catch {
      message.error('Failed to save artifact');
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <Title level={5} style={{ margin: 0 }}>
          Artifact
        </Title>
        <Button size="small" icon={<EditOutlined />} onClick={() => setEditorOpen(true)}>
          Edit
        </Button>
      </div>

      {content ? (
        <div
          className="pct-text-md"
          style={{
            padding: 8,
            background: 'var(--pct-color-bg-light)',
            borderRadius: 4,
            border: '1px solid var(--pct-color-border-light)',
            maxHeight: 300,
            overflow: 'auto',
          }}
        >
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      ) : (
        <Empty description="No artifact content" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      )}

      <ArtifactEditorModal
        open={editorOpen}
        content={content}
        featureId={featureId}
        taskId={taskId}
        onSave={handleSave}
        onCancel={() => setEditorOpen(false)}
      />
    </div>
  );
}
