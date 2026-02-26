import { ConfigProvider, Spin, theme } from 'antd';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';
import { useUIStore } from './stores/uiStore';
import { useProjectStatus } from './hooks/useConfigQueries';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import BoardPage from './pages/BoardPage';
import SettingsPage from './pages/SettingsPage';

const queryClient = new QueryClient();

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  const location = useLocation();
  const { data: status, isLoading } = useProjectStatus(!!token);

  if (!token) return <Navigate to="/login" replace />;
  if (isLoading)
    return <Spin style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }} />;
  if (status && !status.initialized && location.pathname !== '/settings') {
    return <Navigate to="/settings" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';
  const fontSize = useUIStore((s) => s.fontSize);

  return (
    <GoogleOAuthProvider clientId={googleClientId}>
      <QueryClientProvider client={queryClient}>
        <ConfigProvider
          theme={{
            algorithm: theme.compactAlgorithm,
            token: { fontSize, colorTextSecondary: '#3d4a5c' },
          }}
        >
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <HomePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/board"
                element={
                  <ProtectedRoute>
                    <BoardPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/settings"
                element={
                  <ProtectedRoute>
                    <SettingsPage />
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </ConfigProvider>
      </QueryClientProvider>
    </GoogleOAuthProvider>
  );
}
