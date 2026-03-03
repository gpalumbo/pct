import { useState, useEffect } from 'react';
import { Typography, Select, Empty, Spin, Divider } from 'antd';
import PlanningChat from '../components/chat/PlanningChat';
import ArtifactPane from '../components/board/ArtifactPane';
import { chatApi } from '../api/chatApi';

const { Title } = Typography;

/** Parse a session ID like "featureId--taskId" into its parts. */
function parseSessionId(sessionId: string): { featureId: string; taskId: string } | null {
  const parts = sessionId.split('--');
  if (parts.length === 2 && parts[0] && parts[1]) {
    return { featureId: parts[0], taskId: parts[1] };
  }
  return null;
}

export default function PlanningPage() {
  const [sessions, setSessions] = useState<string[]>([]);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    chatApi
      .listSessions()
      .then((list) => {
        setSessions(list);
        if (list.length > 0 && !selectedSession) {
          setSelectedSession(list[0]);
        }
      })
      .finally(() => setLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: '20vh' }} />;

  const parsed = selectedSession ? parseSessionId(selectedSession) : null;

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
          allowClear={false}
        >
          {sessions.map((s) => (
            <Select.Option key={s} value={s}>
              {s}
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
            {parsed ? (
              <ArtifactPane featureId={parsed.featureId} taskId={parsed.taskId} />
            ) : (
              <div>
                <Title level={5} style={{ margin: '0 0 8px 0' }}>
                  Artifact
                </Title>
                <Divider style={{ margin: '8px 0' }} />
                <Empty description="Select a task session to view artifacts" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
