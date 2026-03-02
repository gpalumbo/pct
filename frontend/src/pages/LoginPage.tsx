import { useState } from 'react';
import { useNavigate, useSearchParams, Navigate } from 'react-router-dom';
import { Button, Card, Form, Input, message, Typography } from 'antd';
import { useAuthStore } from '../stores/authStore';
import { configApi } from '../api/configApi';

const { Title } = Typography;

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const login = useAuthStore((s) => s.login);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const returnTo = searchParams.get('returnTo') || '/';

  if (isAuthenticated) return <Navigate to={returnTo} replace />;

  const onFinish = async (values: { email: string; password: string }) => {
    setLoading(true);
    try {
      // Try login first, then register if login fails
      try {
        const data = await configApi.login(values.email, values.password);
        login(data.access_token, values.email);
      } catch {
        const data = await configApi.register(values.email, values.password);
        login(data.access_token, values.email);
      }
      navigate(returnTo, { replace: true });
    } catch {
      message.error('Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
      <Card style={{ width: 400 }}>
        <Title level={3} style={{ textAlign: 'center' }}>
          PCT — Project Construction Tool
        </Title>
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item name="email" label="Email" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="Password" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              Sign In / Register
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
