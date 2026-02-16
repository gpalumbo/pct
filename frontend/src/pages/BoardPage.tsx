import { Button, Layout, Space, Typography } from 'antd';
import { HomeOutlined, SettingOutlined } from '@ant-design/icons';
import { useAuthStore } from '../stores/authStore';
import { useNavigate } from 'react-router-dom';
import KanbanBoard from '../components/board/KanbanBoard';

const { Header, Content } = Layout;
const { Title } = Typography;

export default function BoardPage() {
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
          PCT Board
        </Title>
        <Space>
          <Button icon={<HomeOutlined />} onClick={() => navigate('/')}>Home</Button>
          <Button icon={<SettingOutlined />} onClick={() => navigate('/settings')}>Settings</Button>
          <Button onClick={handleLogout}>Logout</Button>
        </Space>
      </Header>
      <Content style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <KanbanBoard />
      </Content>
    </Layout>
  );
}
