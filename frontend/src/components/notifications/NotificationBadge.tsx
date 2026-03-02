/** Notification badge — bell icon with unread count, opens panel popover. */

import { useState } from 'react';
import { Badge, Popover, Button } from 'antd';
import { BellOutlined } from '@ant-design/icons';
import { useNotificationBadge } from '../../hooks/useNotificationQueries';
import NotificationPanel from './NotificationPanel';

export default function NotificationBadge() {
  const [open, setOpen] = useState(false);
  const { data } = useNotificationBadge();

  const count = data?.badge_count ?? 0;

  return (
    <Popover
      content={<NotificationPanel onClose={() => setOpen(false)} />}
      trigger="click"
      open={open}
      onOpenChange={setOpen}
      placement="bottomRight"
      arrow={false}
      overlayInnerStyle={{ padding: 0 }}
    >
      <Badge count={count} size="small" offset={[-2, 2]}>
        <Button type="text" icon={<BellOutlined />} />
      </Badge>
    </Popover>
  );
}
