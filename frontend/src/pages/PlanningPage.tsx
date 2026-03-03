import { useState, useEffect } from 'react';
import { Typography, Select, Empty, Spin, Divider } from 'antd';
import PlanningChat from '../components/chat/PlanningChat';
import { chatApi } from '../api/chatApi';
import type { ChatSession } from '../types/chat';

const { Title } = Typography;

export default function PlanningPage() {
  const [defaultSessionId, setDefaultSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load the dedicated planning session first, then all sessions for the selector
    Promise.all([chatApi.getDefaultSession(), chatApi.listSessions()])
      .then(([defaultSession, allSessions]) => {
        setDefaultSessionId(defaultSession.id);
        setSessions(allSessions);
        if (!selectedSession) {
          setSelectedSession(defaultSession.id);
        }
      })
      .catch(() => {
        // Fallback: try just listing sessions
        chatApi.listSessions().then((list) => {
          setSessions(list);
          if (list.length > 0 && !selectedSession) {
            setSelectedSession(list[0].id);
          }
        });
      })
      .finally(() => setLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: '20vh' }} />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 64px)', padding: 16, gap: 12 }}>
      {/* Header with session selector */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
        <Title level={4} style={{ margin: 0 }}>
          Planning
        </Title>
        <Select
          value={selectedSession}
          onChange={setSelectedSession}
          placeholder="Select a session"
          style={{ minWidth: 300 }}
          showSearch
          optionFilterProp="children"
          allowClear={false}
        >
          {sessions.map((s) => (
            <Select.Option key={s.id} value={s.id}>
              {s.id === defaultSessionId ? `${s.title || s.id} (default)` : s.title || s.id}
            </Select.Option>
          ))}
        </Select>
      </div>

      {!selectedSession ? (
        <Empty description="No chat sessions found. Start a chat from the Board to create one." />
      ) : (
        <div style={{ display: 'flex', flex: 1, gap: 16, minHeight: 0 }}>
          {/* Left: Chat messages + input */}
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              border: '1px solid #f0f0f0',
              borderRadius: 8,
              padding: 12,
              minHeight: 0,
            }}
          >
            <PlanningChat sessionId={selectedSession} key={selectedSession} />
          </div>

          {/* Right: Artifact viewer */}
          <div
            style={{
              width: 420,
              flexShrink: 0,
              border: '1px solid #f0f0f0',
              borderRadius: 8,
              padding: 12,
              overflow: 'auto',
            }}
          >
            <div>
              <Title level={5} style={{ margin: '0 0 8px 0' }}>
                Artifacts
              </Title>
              <Divider style={{ margin: '8px 0' }} />
              <Empty description="Project planning artifacts (work/INDEX.md)" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
