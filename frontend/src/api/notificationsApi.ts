/** Notifications API wrapper. */

import client from './client';
import type { NotificationListResponse, NotificationBadgeResponse } from '../types/notifications';

export const notificationsApi = {
  list: (params?: { include_acknowledged?: boolean; feature_id?: string; task_id?: string; limit?: number }) =>
    client.get<NotificationListResponse>('/api/notifications/', { params }).then((r) => r.data),

  badge: () => client.get<NotificationBadgeResponse>('/api/notifications/badge').then((r) => r.data),

  acknowledge: (eventId: string) =>
    client.post<{ acknowledged: boolean }>(`/api/notifications/${eventId}/acknowledge`).then((r) => r.data),

  acknowledgeAll: () =>
    client.post<{ acknowledged_count: number }>('/api/notifications/acknowledge-all').then((r) => r.data),
};
