import { Tabs, Typography } from 'antd';
import {
  SettingOutlined,
  AppstoreOutlined,
  ExperimentOutlined,
  TeamOutlined,
  NodeIndexOutlined,
  FileTextOutlined,
  UserOutlined,
} from '@ant-design/icons';
import GeneralTab from '../components/settings/GeneralTab';
import ModelRegistryTab from '../components/settings/ModelRegistryTab';
import LoRARegistryTab from '../components/settings/LoRARegistryTab';
import AgentsTab from '../components/settings/AgentsTab';
import WorkflowTab from '../components/settings/WorkflowTab';
import ArtifactTypesTab from '../components/settings/ArtifactTypesTab';

const { Title } = Typography;

const tabItems = [
  {
    key: 'general',
    label: 'General',
    icon: <SettingOutlined />,
    children: <GeneralTab />,
  },
  {
    key: 'models',
    label: 'Model Registry',
    icon: <AppstoreOutlined />,
    children: <ModelRegistryTab />,
  },
  {
    key: 'lora',
    label: 'LoRA Registry',
    icon: <ExperimentOutlined />,
    children: <LoRARegistryTab />,
  },
  {
    key: 'agents',
    label: 'Agents',
    icon: <TeamOutlined />,
    children: <AgentsTab />,
  },
  {
    key: 'workflow',
    label: 'Workflow',
    icon: <NodeIndexOutlined />,
    children: <WorkflowTab />,
  },
  {
    key: 'artifacts',
    label: 'Artifact Types',
    icon: <FileTextOutlined />,
    children: <ArtifactTypesTab />,
  },
  {
    key: 'users',
    label: 'Users',
    icon: <UserOutlined />,
    children: (
      <div style={{ padding: 24 }}>
        <Title level={5}>Users</Title>
        <p>User management will be available here.</p>
      </div>
    ),
  },
];

export default function SettingsPage() {
  return (
    <div style={{ padding: 24 }}>
      <Title level={3} style={{ marginBottom: 16 }}>
        Settings
      </Title>
      <Tabs
        tabPosition="left"
        items={tabItems}
        style={{ minHeight: 'calc(100vh - 120px)' }}
      />
    </div>
  );
}
