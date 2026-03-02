import { useState } from 'react';
import { Typography, Button, Space } from 'antd';
import { PlusOutlined, SettingOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useProject } from '../../hooks/useConfigQueries';
import CreateFeatureModal from './CreateFeatureModal';
import NotificationBadge from '../notifications/NotificationBadge';

const { Title } = Typography;

export default function BoardHeader() {
  const { data: project } = useProject();
  const navigate = useNavigate();
  const [showCreate, setShowCreate] = useState(false);

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <Title level={4} style={{ margin: 0 }}>
          {project?.name ?? 'PCT Board'}
        </Title>
        <Space>
          <NotificationBadge />
          <Button icon={<PlusOutlined />} type="primary" onClick={() => setShowCreate(true)}>
            New Feature
          </Button>
          <Button icon={<SettingOutlined />} onClick={() => navigate('/settings')}>
            Settings
          </Button>
        </Space>
      </div>
      <CreateFeatureModal open={showCreate} onClose={() => setShowCreate(false)} />
    </>
  );
}
