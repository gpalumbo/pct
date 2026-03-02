import { useState } from 'react';
import { Button, Spin, Typography, Empty } from 'antd';
import { EditOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import { boardApi } from '../../api/boardApi';
import ArtifactEditorModal from './ArtifactEditorModal';

const { Title } = Typography;

interface ArtifactPaneProps {
  featureId: string;
  taskId: string;
}

export default function ArtifactPane({ featureId, taskId }: ArtifactPaneProps) {
  const [editorOpen, setEditorOpen] = useState(false);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['artifact', featureId, taskId],
    queryFn: () => boardApi.getArtifact(featureId, taskId),
    enabled: !!featureId && !!taskId,
  });

  if (isLoading) return <Spin size="small" />;

  const content = data?.content ?? '';

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
          style={{
            padding: 8,
            background: '#fafafa',
            borderRadius: 4,
            border: '1px solid #f0f0f0',
            maxHeight: 300,
            overflow: 'auto',
            fontSize: 13,
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
        onClose={() => {
          setEditorOpen(false);
          refetch();
        }}
      />
    </div>
  );
}
