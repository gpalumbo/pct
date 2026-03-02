import { Typography, Empty } from 'antd';
import ReactMarkdown from 'react-markdown';

const { Title } = Typography;

interface ArtifactOutputPaneProps {
  inputContent: string;
  outputContent: string;
}

export default function ArtifactOutputPane({ inputContent, outputContent }: ArtifactOutputPaneProps) {
  return (
    <div style={{ display: 'flex', gap: 12, height: '100%' }}>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Title level={5} style={{ margin: '0 0 8px 0' }}>
          Input
        </Title>
        <div
          style={{
            flex: 1,
            padding: 8,
            background: '#fafafa',
            border: '1px solid #f0f0f0',
            borderRadius: 4,
            overflow: 'auto',
            fontSize: 13,
          }}
        >
          {inputContent ? (
            <ReactMarkdown>{inputContent}</ReactMarkdown>
          ) : (
            <Empty description="No input" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Title level={5} style={{ margin: '0 0 8px 0' }}>
          Output
        </Title>
        <div
          style={{
            flex: 1,
            padding: 8,
            background: '#fafafa',
            border: '1px solid #f0f0f0',
            borderRadius: 4,
            overflow: 'auto',
            fontSize: 13,
          }}
        >
          {outputContent ? (
            <ReactMarkdown>{outputContent}</ReactMarkdown>
          ) : (
            <Empty description="No output yet" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </div>
      </div>
    </div>
  );
}
