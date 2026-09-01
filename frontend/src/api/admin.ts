import { request } from './client';

export interface AdminOverview {
  total_users: number;
  active_users: number;
  suspended_users: number;
  total_workspaces: number;
  active_workspaces: number;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  cancelled_executions: number;
  active_capabilities: number;
  active_mcp_servers: number;
  active_workflows: number;
  avg_latency_ms: number;
  success_rate: number;
  system_status: string;
  alerts_count: number;
  security_alerts_count: number;
  time_window: string;
}

export interface AdminUserWorkspaceInfo {
  workspace_id: string;
  workspace_name: string;
  role: string;
}

export interface AdminUserListItem {
  id: string;
  email: string;
  username: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  is_deleted: boolean;
  created_at: string;
  last_activity?: string | null;
  workspaces_count: number;
  workspaces: AdminUserWorkspaceInfo[];
}

export interface AdminUserListResponse {
  total: number;
  page: number;
  page_size: number;
  users: AdminUserListItem[];
}

export interface AdminUserDetailResponse {
  id: string;
  email: string;
  username: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  is_deleted: boolean;
  avatar_url?: string | null;
  settings: Record<string, any>;
  created_at: string;
  workspaces: AdminUserWorkspaceInfo[];
  recent_audit_logs: Array<{
    id: string;
    action: string;
    ip_address?: string | null;
    details?: string | null;
    created_at: string;
  }>;
}

export interface AdminWorkspaceListItem {
  id: string;
  name: string;
  organization_id: string;
  created_at: string;
  members_count: number;
  documents_count: number;
  workflows_count: number;
  mcp_servers_count: number;
  executions_count: number;
  status: string;
}

export interface AdminWorkspaceListResponse {
  total: number;
  page: number;
  page_size: number;
  workspaces: AdminWorkspaceListItem[];
}

export interface AdminRolePermissionResponse {
  roles: Array<{
    id: string;
    name: string;
    description?: string | null;
    users_count: number;
  }>;
  permission_matrix: Array<Record<string, any>>;
  capability_permissions: Array<{
    capability_id: string;
    name: string;
    capability_type: string;
    required_permissions: string[];
    scope: string;
  }>;
}

export interface SubsystemHealth {
  name: string;
  status: string;
  latency_ms: number;
  details: Record<string, any>;
}

export interface AdminSystemHealthResponse {
  overall_status: string;
  timestamp: number;
  environment: string;
  subsystems: SubsystemHealth[];
}

export interface AdminExecutionListItem {
  execution_id: string;
  capability_id: string;
  capability_name?: string | null;
  status: string;
  workspace_id: string;
  user_id?: string | null;
  duration_ms: number;
  started_at: string;
  completed_at?: string | null;
  correlation_id: string;
  errors_count: number;
}

export interface AdminExecutionListResponse {
  total: number;
  page: number;
  page_size: number;
  executions: AdminExecutionListItem[];
}

export interface AdminAuditLogItem {
  id: string;
  user_id?: string | null;
  username?: string | null;
  action: string;
  ip_address?: string | null;
  details?: string | null;
  created_at: string;
}

export interface AdminAuditLogListResponse {
  total: number;
  page: number;
  page_size: number;
  logs: AdminAuditLogItem[];
}

export interface AdminSecurityPostureResponse {
  tenant_isolation_enforced: boolean;
  rbac_posture: string;
  confirmation_gate_active: boolean;
  ssrf_defense_active: boolean;
  secret_redaction_active: boolean;
  total_security_denials: number;
  recent_denials: Array<Record<string, any>>;
  recent_alerts: Array<Record<string, any>>;
}

export interface AdminActivityFeedItem {
  event_id: string;
  event_type: string;
  source_component: string;
  workspace_id?: string | null;
  user_id?: string | null;
  timestamp: string;
  summary: string;
  payload: Record<string, any>;
}

export interface AdminActivityFeedResponse {
  total: number;
  events: AdminActivityFeedItem[];
}

export interface AdminConfigResponse {
  environment: string;
  max_execution_timeout_seconds: number;
  max_concurrency_per_workspace: number;
  max_intelligence_depth: number;
  max_intelligence_steps: number;
  features_enabled: Record<string, boolean>;
}

export interface AdminExportRequest {
  export_type: 'executions' | 'usage' | 'failures' | 'audit_logs';
  format: 'json' | 'csv';
  time_window?: string;
  limit?: number;
}

export interface AdminExportResponse {
  export_type: string;
  format: string;
  record_count: number;
  generated_at: string;
  content: string;
}

export async function getAdminOverview(timeWindow: string = '24h'): Promise<AdminOverview> {
  return request<AdminOverview>(`/admin/overview?time_window=${encodeURIComponent(timeWindow)}`);
}

export async function getAdminUsers(params: {
  page?: number;
  page_size?: number;
  search?: string;
  role?: string;
  is_active?: boolean;
} = {}): Promise<AdminUserListResponse> {
  const query = new URLSearchParams();
  if (params.page) query.append('page', params.page.toString());
  if (params.page_size) query.append('page_size', params.page_size.toString());
  if (params.search) query.append('search', params.search);
  if (params.role) query.append('role', params.role);
  if (params.is_active !== undefined) query.append('is_active', params.is_active.toString());
  
  const qStr = query.toString() ? `?${query.toString()}` : '';
  return request<AdminUserListResponse>(`/admin/users${qStr}`);
}

export async function getAdminUserDetail(userId: string): Promise<AdminUserDetailResponse> {
  return request<AdminUserDetailResponse>(`/admin/users/${encodeURIComponent(userId)}`);
}

export async function updateAdminUserStatus(userId: string, isActive: boolean, reason?: string): Promise<{ message: string; user_id: string; is_active: boolean }> {
  return request<{ message: string; user_id: string; is_active: boolean }>(`/admin/users/${encodeURIComponent(userId)}/status`, {
    method: 'PUT',
    body: JSON.stringify({ is_active: isActive, reason })
  });
}

export async function updateAdminUserRole(userId: string, roleName: string): Promise<{ message: string; user_id: string; role: string }> {
  return request<{ message: string; user_id: string; role: string }>(`/admin/users/${encodeURIComponent(userId)}/role`, {
    method: 'PUT',
    body: JSON.stringify({ role_name: roleName })
  });
}

export async function getAdminWorkspaces(params: {
  page?: number;
  page_size?: number;
  search?: string;
} = {}): Promise<AdminWorkspaceListResponse> {
  const query = new URLSearchParams();
  if (params.page) query.append('page', params.page.toString());
  if (params.page_size) query.append('page_size', params.page_size.toString());
  if (params.search) query.append('search', params.search);
  const qStr = query.toString() ? `?${query.toString()}` : '';
  return request<AdminWorkspaceListResponse>(`/admin/workspaces${qStr}`);
}

export async function getAdminRolesPermissions(): Promise<AdminRolePermissionResponse> {
  return request<AdminRolePermissionResponse>('/admin/roles-permissions');
}

export async function getAdminSystemHealth(): Promise<AdminSystemHealthResponse> {
  return request<AdminSystemHealthResponse>('/admin/system-health');
}

export async function getAdminExecutions(params: {
  page?: number;
  page_size?: number;
  capability_id?: string;
  status_filter?: string;
  search?: string;
} = {}): Promise<AdminExecutionListResponse> {
  const query = new URLSearchParams();
  if (params.page) query.append('page', params.page.toString());
  if (params.page_size) query.append('page_size', params.page_size.toString());
  if (params.capability_id) query.append('capability_id', params.capability_id);
  if (params.status_filter) query.append('status_filter', params.status_filter);
  if (params.search) query.append('search', params.search);
  const qStr = query.toString() ? `?${query.toString()}` : '';
  return request<AdminExecutionListResponse>(`/admin/executions${qStr}`);
}

export async function getAdminAuditLogs(params: {
  page?: number;
  page_size?: number;
  user_id?: string;
  action?: string;
  search?: string;
} = {}): Promise<AdminAuditLogListResponse> {
  const query = new URLSearchParams();
  if (params.page) query.append('page', params.page.toString());
  if (params.page_size) query.append('page_size', params.page_size.toString());
  if (params.user_id) query.append('user_id', params.user_id);
  if (params.action) query.append('action', params.action);
  if (params.search) query.append('search', params.search);
  const qStr = query.toString() ? `?${query.toString()}` : '';
  return request<AdminAuditLogListResponse>(`/admin/audit-logs${qStr}`);
}

export async function getAdminSecurityPosture(): Promise<AdminSecurityPostureResponse> {
  return request<AdminSecurityPostureResponse>('/admin/security-posture');
}

export async function getAdminActivityFeed(limit: number = 50): Promise<AdminActivityFeedResponse> {
  return request<AdminActivityFeedResponse>(`/admin/activity-feed?limit=${limit}`);
}

export async function getAdminConfig(): Promise<AdminConfigResponse> {
  return request<AdminConfigResponse>('/admin/config');
}

export async function exportAdminReport(payload: AdminExportRequest): Promise<AdminExportResponse> {
  return request<AdminExportResponse>('/admin/export', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}
