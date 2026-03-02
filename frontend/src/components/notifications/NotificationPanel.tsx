/** Notification panel — dropdown list of recent notifications. */

import { List, Button, Typography, Empty, Tag } from 'antd';
import { CheckOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import {
  useNotifications,
  useAcknowledgeMutation,
  useAcknowledgeAllMutation,
} from '../../hooks/useNotificationQueries';
import type { NotificationEvent } from '../../types/notifications';
import type { NotificationState } from '../../types/enums';

dayjs.extend(relativeTime);

const { Text } = Typography;

const SEVERITY_COLOR: Record<NotificationState, string> = {
  attention: 'blue',
  warning: 'orange',
  ready: 'green',
};

const SEVERITY_LABEL: Record<NotificationState, string> = {
  attention: 'Attention',
  warning: 'Warning',
  ready: 'Ready',
};

interface NotificationPanelProps {
  onClose?: () => void;
}

export default function NotificationPanel({ onClose }: NotificationPanelProps) {
  const { data, isLoading } = useNotifications();
  const acknowledgeMut = useAcknowledgeMutation();
  const acknowledgeAllMut = useAcknowledgeAllMutation();

  const events = data?.events ?? [];

  const handleAcknowledge = (id: string) => {
    acknowledgeMut.mutate(id);
  };

  const handleAcknowledgeAll = () => {
    acknowledgeAllMut.mutate(undefined, {
      onSuccess: () => onClose?.(),
    });
  };

  return (
    <div style={{ width: 380, maxHeight: 440, overflow: 'auto' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '8px 12px',
          borderBottom: '1px solid #f0f0f0',
        }}
      >
        <Text strong>Notifications</Text>
        {events.length > 0 && (
          <Button
            type="link"
            size="small"
            icon={<CheckOutlined />}
            onClick={handleAcknowledgeAll}
            loading={acknowledgeAllMut.isPending}
          >
            Mark all read
          </Button>
        )}
      </div>
      {events.length === 0 && !isLoading ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="No notifications"
          style={{ padding: '24px 0' }}
        />
      ) : (
        <List
          loading={isLoading}
          dataSource={events}
          renderItem={(item: NotificationEvent) => (
            <List.Item
              key={item.id}
              style={{ padding: '8px 12px', cursor: 'pointer' }}
              onClick={() => handleAcknowledge(item.id)}
              actions={[
                <Button
                  key="ack"
                  type="text"
                  size="small"
                  icon={<CheckOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleAcknowledge(item.id);
                  }}
                />,
              ]}
            >
              <List.Item.Meta
                title={
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Tag color={SEVERITY_COLOR[item.severity]} style={{ marginInlineEnd: 0 }}>
                      {SEVERITY_LABEL[item.severity]}
                    </Tag>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {dayjs(item.created_at).fromNow()}
                    </Text>
                  </div>
                }
                description={
                  <Text style={{ fontSize: 13 }}>{item.message}</Text>
                }
              />
            </List.Item>
          )}
        />
      )}
    </div>
  );
}
