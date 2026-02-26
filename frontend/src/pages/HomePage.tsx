import { Button, Layout, Space, Typography } from 'antd';
import { AppstoreOutlined, SettingOutlined } from '@ant-design/icons';
import { useAuthStore } from '../stores/authStore';
import { useNavigate } from 'react-router-dom';
import PlanningChat from '../components/chat/PlanningChat';

const { Header, Content } = Layout;
const { Title } = Typography;

export default function HomePage() {
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <Layout style={{ height: '100vh' }}>
      <Header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4} style={{ color: 'white', margin: 0 }}>
          PCT
        </Title>
        <Space>
          <Button icon={<AppstoreOutlined />} onClick={() => navigate('/board')}>
            Board
          </Button>
          <Button icon={<SettingOutlined />} onClick={() => navigate('/settings')}>
            Settings
          </Button>
          <Button onClick={handleLogout}>Logout</Button>
        </Space>
      </Header>
      <Content style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <PlanningChat />
      </Content>
    </Layout>
  );
}
