import { request } from './client';

export interface NotificationItem {
  id: string;
  workspace_id: string;
  recipient_user_id: string;
  actor_user_id?: string | null;
  actor_name?: string | null;
  type: string;
  title: string;
  body: string;
  resource_type?: string | null;
  resource_id?: string | null;
  project_id?: string | null;
  team_id?: string | null;
  comment_id?: string | null;
  status: 'unread' | 'read';
  read_at?: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  total: number;
  unread_count: number;
  page: number;
  page_size: number;
  notifications: NotificationItem[];
}

export interface UnreadCountResponse {
  unread_count: number;
}

export interface NotificationPreferenceItem {
  notification_type: string;
  in_app_enabled: boolean;
  email_enabled: boolean;
  push_enabled: boolean;
}

export interface NotificationPreferenceResponse {
  user_id: string;
  preferences: NotificationPreferenceItem[];
}

export async function getNotifications(params?: {
  status?: string;
  type?: string;
  page?: number;
  page_size?: number;
}): Promise<NotificationListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.append('status', params.status);
  if (params?.type) query.append('type', params.type);
  if (params?.page) query.append('page', params.page.toString());
  if (params?.page_size) query.append('page_size', params.page_size.toString());

  const qStr = query.toString() ? `?${query.toString()}` : '';
  return request<NotificationListResponse>(`/notifications${qStr}`);
}

export async function getUnreadNotificationCount(): Promise<UnreadCountResponse> {
  return request<UnreadCountResponse>('/notifications/unread-count');
}

export async function markNotificationRead(notificationId: string): Promise<NotificationItem> {
  return request<NotificationItem>(`/notifications/${encodeURIComponent(notificationId)}/read`, {
    method: 'POST',
  });
}

export async function markAllNotificationsRead(): Promise<UnreadCountResponse> {
  return request<UnreadCountResponse>('/notifications/read-all', {
    method: 'POST',
  });
}

export async function getNotificationPreferences(): Promise<NotificationPreferenceResponse> {
  return request<NotificationPreferenceResponse>('/notifications/preferences');
}

export async function updateNotificationPreference(data: {
  notification_type: string;
  in_app_enabled?: boolean;
  email_enabled?: boolean;
  push_enabled?: boolean;
}): Promise<NotificationPreferenceResponse> {
  return request<NotificationPreferenceResponse>('/notifications/preferences', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}
