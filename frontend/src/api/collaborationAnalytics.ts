import { request } from './client';

export interface PeriodComparison {
  current: number;
  previous: number;
  delta: number;
  growth_rate: number;
}

export interface CollaborationOverview {
  workspace_id: string;
  time_window: string;
  active_users: number;
  total_members: number;
  active_teams: number;
  active_projects: number;
  total_comments: number;
  root_comments: number;
  total_replies: number;
  total_mentions: number;
  notifications_generated: number;
  notifications_read: number;
  total_activities: number;
  engagement_rate: number;
  health_status: 'HEALTHY' | 'MODERATE' | 'LOW';
  activity_growth: PeriodComparison;
  comment_growth: PeriodComparison;
}

export interface TeamAnalyticsItem {
  team_id: string;
  team_name: string;
  member_count: number;
  active_members: number;
  comment_count: number;
  activity_count: number;
  engagement_rate: number;
  health_status: string;
}

export interface TeamAnalyticsListResponse {
  total: number;
  page: number;
  page_size: number;
  teams: TeamAnalyticsItem[];
}

export interface ProjectAnalyticsItem {
  project_id: string;
  project_name: string;
  member_count: number;
  active_members: number;
  resource_count: number;
  comment_count: number;
  reply_count: number;
  activity_count: number;
  engagement_rate: number;
}

export interface ProjectAnalyticsListResponse {
  total: number;
  page: number;
  page_size: number;
  projects: ProjectAnalyticsItem[];
}

export interface ActivityTimeSeriesPoint {
  date: string;
  count: number;
  by_type: Record<string, number>;
}

export interface ActivityAnalyticsResponse {
  time_window: string;
  total_activities: number;
  series: ActivityTimeSeriesPoint[];
}

export interface TopContributorItem {
  user_id: string;
  username: string;
  activity_count: number;
  comment_count: number;
  mention_count: number;
}

export interface TopContributorsResponse {
  contributors: TopContributorItem[];
}

export async function getCollaborationOverview(timeWindow = '7d'): Promise<CollaborationOverview> {
  return request<CollaborationOverview>(`/collaboration/analytics/overview?time_window=${encodeURIComponent(timeWindow)}`);
}

export async function getTeamAnalytics(params?: { page?: number; page_size?: number; search?: string }): Promise<TeamAnalyticsListResponse> {
  const q = new URLSearchParams();
  if (params?.page) q.append('page', params.page.toString());
  if (params?.page_size) q.append('page_size', params.page_size.toString());
  if (params?.search) q.append('search', params.search);
  const qStr = q.toString() ? `?${q.toString()}` : '';
  return request<TeamAnalyticsListResponse>(`/collaboration/analytics/teams${qStr}`);
}

export async function getProjectAnalytics(params?: { page?: number; page_size?: number; search?: string }): Promise<ProjectAnalyticsListResponse> {
  const q = new URLSearchParams();
  if (params?.page) q.append('page', params.page.toString());
  if (params?.page_size) q.append('page_size', params.page_size.toString());
  if (params?.search) q.append('search', params.search);
  const qStr = q.toString() ? `?${q.toString()}` : '';
  return request<ProjectAnalyticsListResponse>(`/collaboration/analytics/projects${qStr}`);
}

export async function getActivityAnalytics(timeWindow = '7d'): Promise<ActivityAnalyticsResponse> {
  return request<ActivityAnalyticsResponse>(`/collaboration/analytics/activity?time_window=${encodeURIComponent(timeWindow)}`);
}

export async function getTopContributors(limit = 10): Promise<TopContributorsResponse> {
  return request<TopContributorsResponse>(`/collaboration/analytics/top-contributors?limit=${limit}`);
}
