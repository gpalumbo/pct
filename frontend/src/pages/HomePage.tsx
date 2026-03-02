import { Typography, Spin } from 'antd';
import { useProjectStatus } from '../hooks/useConfigQueries';

const { Title, Paragraph } = Typography;

export default function HomePage() {
  const { data: status, isLoading } = useProjectStatus();

  if (isLoading) return <Spin size="large" />;

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>PCT — Project Construction Tool</Title>
      <Paragraph>
        Project <strong>{status?.project_name}</strong> is initialized. Use the sidebar to navigate.
      </Paragraph>
    </div>
  );
}
