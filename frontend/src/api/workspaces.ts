import { request } from './client';

export interface WorkspaceMemberDetail {
  id: string;
  workspace_id: string;
  user_id: string;
  username: string;
  email: string;
  role: 'owner' | 'admin' | 'member' | 'viewer';
  created_at: string;
  updated_at?: string | null;
}

export interface WorkspaceMemberListResponse {
  total: number;
  page: number;
  page_size: number;
  members: WorkspaceMemberDetail[];
}

export interface EffectivePermissionsResponse {
  user_id: string;
  workspace_id: string;
  team_id?: string | null;
  workspace_role?: string | null;
  team_role?: string | null;
  permissions: string[];
}

export interface PermissionRegistryResponse {
  permissions: string[];
  workspace_roles: Record<string, string[]>;
  team_roles: Record<string, string[]>;
}

export async function getWorkspaceMembers(
  workspaceId: string,
  params?: {
    page?: number;
    page_size?: number;
    search?: string;
  }
): Promise<WorkspaceMemberListResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.append('page', params.page.toString());
  if (params?.page_size) query.append('page_size', params.page_size.toString());
  if (params?.search) query.append('search', params.search);

  const qStr = query.toString() ? `?${query.toString()}` : '';
  return request<WorkspaceMemberListResponse>(`/workspaces/${encodeURIComponent(workspaceId)}/members${qStr}`);
}

export async function updateWorkspaceMemberRole(
  workspaceId: string,
  userId: string,
  newRole: string
): Promise<WorkspaceMemberDetail> {
  return request<WorkspaceMemberDetail>(`/workspaces/${encodeURIComponent(workspaceId)}/members/${encodeURIComponent(userId)}/role`, {
    method: 'PUT',
    body: JSON.stringify({ role: newRole }),
  });
}

export async function transferWorkspaceOwnership(
  workspaceId: string,
  targetUserId: string
): Promise<WorkspaceMemberDetail> {
  return request<WorkspaceMemberDetail>(`/workspaces/${encodeURIComponent(workspaceId)}/transfer-ownership`, {
    method: 'POST',
    body: JSON.stringify({ target_user_id: targetUserId }),
  });
}

export async function getEffectivePermissions(
  workspaceId: string,
  teamId?: string
): Promise<EffectivePermissionsResponse> {
  const query = new URLSearchParams();
  if (teamId) query.append('team_id', teamId);
  const qStr = query.toString() ? `?${query.toString()}` : '';
  return request<EffectivePermissionsResponse>(`/workspaces/${encodeURIComponent(workspaceId)}/effective-permissions${qStr}`);
}

export async function getPermissionRegistry(): Promise<PermissionRegistryResponse> {
  return request<PermissionRegistryResponse>('/permissions');
}
