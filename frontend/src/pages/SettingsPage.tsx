import { Button, Layout, Tabs, Typography } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import GeneralTab from '../components/settings/GeneralTab';
import ModelRegistryTab from '../components/settings/ModelRegistryTab';
import LoRARegistryTab from '../components/settings/LoRARegistryTab';
import AgentsTab from '../components/settings/AgentsTab';
import WorkflowTab from '../components/settings/WorkflowTab';

const { Header, Content } = Layout;
const { Title } = Typography;

export default function SettingsPage() {
  const navigate = useNavigate();

  const items = [
    { key: 'general', label: 'General', children: <GeneralTab /> },
    { key: 'models', label: 'Model Registry', children: <ModelRegistryTab /> },
    { key: 'loras', label: 'LoRA Registry', children: <LoRARegistryTab /> },
    { key: 'agents', label: 'Agents', children: <AgentsTab /> },
    { key: 'workflow', label: 'Workflow Stages', children: <WorkflowTab /> },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')} />
        <Title level={4} style={{ color: 'white', margin: 0 }}>
          Project Settings
        </Title>
      </Header>
      <Content style={{ padding: 24 }}>
        <Tabs items={items} />
      </Content>
    </Layout>
  );
}
