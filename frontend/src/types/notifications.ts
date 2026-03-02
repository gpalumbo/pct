/** Notification types — mirrors backend models. */

import type { NotificationEventType, NotificationState } from './enums';

export interface NotificationEvent {
  id: string;
  event_type: NotificationEventType;
  task_id: string | null;
  feature_id: string | null;
  message: string;
  severity: NotificationState;
  acknowledged: boolean;
  email_sent: boolean;
  email_target: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  events: NotificationEvent[];
  badge_count: number;
}

export interface NotificationBadgeResponse {
  badge_count: number;
}
