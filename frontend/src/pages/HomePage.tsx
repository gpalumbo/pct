import { Button, Layout, Typography } from 'antd';
import { useAuthStore } from '../stores/authStore';
import { useNavigate } from 'react-router-dom';

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
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4} style={{ color: 'white', margin: 0 }}>
          PCT
        </Title>
        <Button onClick={handleLogout}>Logout</Button>
      </Header>
      <Content style={{ padding: 24 }}>
        <Title level={3}>Welcome to PCT</Title>
        <p>Project Curation Tool is ready.</p>
      </Content>
    </Layout>
  );
}
