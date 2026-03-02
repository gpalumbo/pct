import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider, theme, Layout, Menu, Button, Space, Spin, Typography } from "antd";
import { LogoutOutlined } from "@ant-design/icons";
import { useAuthStore } from "./stores/authStore";
import { useProjectStatus } from "./hooks/useConfigQueries";
import LoginPage from "./pages/LoginPage";
import HomePage from "./pages/HomePage";
import BoardPage from "./pages/BoardPage";
import SettingsPage from "./pages/SettingsPage";
import TrainingPage from "./pages/TrainingPage";
import PertPage from "./pages/PertPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 5000 },
  },
});

function AppHeader() {
  const email = useAuthStore((s) => s.email);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <Layout.Header style={{ display: "flex", alignItems: "center", padding: "0 16px" }}>
      <Typography.Text strong style={{ color: "#fff", fontSize: 16, marginRight: 24, whiteSpace: "nowrap" }}>
        PCT
      </Typography.Text>
      <Menu
        theme="dark"
        mode="horizontal"
        selectedKeys={[location.pathname]}
        items={[
          { key: "/", label: "Home" },
          { key: "/board", label: "Board" },
          { key: "/pert", label: "PERT" },
          { key: "/training", label: "Training" },
          { key: "/settings", label: "Settings" },
        ]}
        onClick={({ key }) => navigate(key)}
        style={{ flex: 1, minWidth: 0 }}
      />
      <Space>
        <Typography.Text style={{ color: "rgba(255,255,255,0.65)" }}>{email}</Typography.Text>
        <Button type="text" icon={<LogoutOutlined />} onClick={handleLogout} style={{ color: "#fff" }}>
          Logout
        </Button>
      </Space>
    </Layout.Header>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const location = useLocation();
  if (!isAuthenticated) {
    const returnTo = location.pathname + location.search;
    return <Navigate to={`/login?returnTo=${encodeURIComponent(returnTo)}`} replace />;
  }
  return <>{children}</>;
}

function ProjectGuard({ children }: { children: React.ReactNode }) {
  const { data: status, isLoading } = useProjectStatus();
  if (isLoading) return <Spin spinning style={{ display: "flex", justifyContent: "center", marginTop: "40vh" }} />;
  if (!status?.initialized) return <Navigate to="/settings" replace />;
  return <>{children}</>;
}

function AppShell() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const location = useLocation();
  const showHeader = isAuthenticated && location.pathname !== "/login";

  return (
    <Layout style={{ minHeight: "100vh" }}>
      {showHeader && <AppHeader />}
      <Layout.Content>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <SettingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <ProjectGuard>
                  <HomePage />
                </ProjectGuard>
              </ProtectedRoute>
            }
          />
          <Route
            path="/board"
            element={
              <ProtectedRoute>
                <ProjectGuard>
                  <BoardPage />
                </ProjectGuard>
              </ProtectedRoute>
            }
          />
          <Route
            path="/pert"
            element={
              <ProtectedRoute>
                <ProjectGuard>
                  <PertPage />
                </ProjectGuard>
              </ProtectedRoute>
            }
          />
          <Route
            path="/training"
            element={
              <ProtectedRoute>
                <ProjectGuard>
                  <TrainingPage />
                </ProjectGuard>
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout.Content>
    </Layout>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider theme={{ algorithm: theme.compactAlgorithm }}>
        <BrowserRouter>
          <AppShell />
        </BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  );
}
