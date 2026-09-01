import { request } from './client';

export interface Team {
  id: string;
  workspace_id: string;
  name: string;
  description?: string | null;
  status: 'active' | 'archived';
  created_by?: string | null;
  created_at: string;
  updated_at?: string | null;
  member_count: number;
  owner_id?: string | null;
  owner_name?: string | null;
}

export interface TeamListResponse {
  total: number;
  page: number;
  page_size: number;
  teams: Team[];
}

export interface TeamMember {
  id: string;
  team_id: string;
  user_id: string;
  username: string;
  email: string;
  role: 'owner' | 'member';
  status: 'active' | 'removed';
  created_at: string;
  updated_at?: string | null;
}

export interface TeamMemberListResponse {
  total: number;
  page: number;
  page_size: number;
  members: TeamMember[];
}

export interface EligibleMember {
  user_id: string;
  username: string;
  email: string;
  workspace_role: string;
}

export interface EligibleMemberListResponse {
  total: number;
  members: EligibleMember[];
}

export interface TeamInvitation {
  id: string;
  team_id: string;
  workspace_id: string;
  invited_user_id?: string | null;
  invited_email?: string | null;
  invited_by?: string | null;
  role: string;
  status: 'pending' | 'accepted' | 'expired' | 'revoked';
  expires_at: string;
  accepted_at?: string | null;
  created_at: string;
}

export interface TeamInvitationListResponse {
  total: number;
  page: number;
  page_size: number;
  invitations: TeamInvitation[];
}

export interface TeamCreatePayload {
  name: string;
  description?: string;
}

export interface TeamUpdatePayload {
  name?: string;
  description?: string;
}

export interface TeamMemberAddPayload {
  user_id: string;
  role?: string;
}

export interface TeamInvitationCreatePayload {
  invited_user_id?: string;
  invited_email?: string;
  role?: string;
}

export async function getTeams(params?: {
  page?: number;
  page_size?: number;
  status?: string;
  search?: string;
}): Promise<TeamListResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.append('page', params.page.toString());
  if (params?.page_size) query.append('page_size', params.page_size.toString());
  if (params?.status) query.append('status', params.status);
  if (params?.search) query.append('search', params.search);

  const qStr = query.toString() ? `?${query.toString()}` : '';
  return request<TeamListResponse>(`/teams${qStr}`);
}

export async function getTeam(teamId: string): Promise<Team> {
  return request<Team>(`/teams/${encodeURIComponent(teamId)}`);
}

export async function createTeam(payload: TeamCreatePayload): Promise<Team> {
  return request<Team>('/teams', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateTeam(teamId: string, payload: TeamUpdatePayload): Promise<Team> {
  return request<Team>(`/teams/${encodeURIComponent(teamId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function archiveTeam(teamId: string): Promise<Team> {
  return request<Team>(`/teams/${encodeURIComponent(teamId)}/archive`, {
    method: 'POST',
  });
}

export async function restoreTeam(teamId: string): Promise<Team> {
  return request<Team>(`/teams/${encodeURIComponent(teamId)}/restore`, {
    method: 'POST',
  });
}

export async function transferTeamOwnership(teamId: string, targetUserId: string): Promise<Team> {
  return request<Team>(`/teams/${encodeURIComponent(teamId)}/transfer-ownership`, {
    method: 'POST',
    body: JSON.stringify({ target_user_id: targetUserId }),
  });
}

export async function getTeamMembers(teamId: string, params?: {
  page?: number;
  page_size?: number;
}): Promise<TeamMemberListResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.append('page', params.page.toString());
  if (params?.page_size) query.append('page_size', params.page_size.toString());

  const qStr = query.toString() ? `?${query.toString()}` : '';
  return request<TeamMemberListResponse>(`/teams/${encodeURIComponent(teamId)}/members${qStr}`);
}

export async function getEligibleMembers(teamId: string, search?: string): Promise<EligibleMemberListResponse> {
  const query = new URLSearchParams();
  if (search) query.append('search', search);
  const qStr = query.toString() ? `?${query.toString()}` : '';
  return request<EligibleMemberListResponse>(`/teams/${encodeURIComponent(teamId)}/eligible-members${qStr}`);
}

export async function addTeamMember(teamId: string, payload: TeamMemberAddPayload): Promise<TeamMember> {
  return request<TeamMember>(`/teams/${encodeURIComponent(teamId)}/members`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function removeTeamMember(teamId: string, userId: string): Promise<{ message: string }> {
  return request<{ message: string }>(`/teams/${encodeURIComponent(teamId)}/members/${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  });
}

export async function createTeamInvitation(teamId: string, payload: TeamInvitationCreatePayload): Promise<TeamInvitation> {
  return request<TeamInvitation>(`/teams/${encodeURIComponent(teamId)}/invitations`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getTeamInvitations(teamId: string, params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<TeamInvitationListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.append('status', params.status);
  if (params?.page) query.append('page', params.page.toString());
  if (params?.page_size) query.append('page_size', params.page_size.toString());

  const qStr = query.toString() ? `?${query.toString()}` : '';
  return request<TeamInvitationListResponse>(`/teams/${encodeURIComponent(teamId)}/invitations${qStr}`);
}

export async function acceptTeamInvitation(invitationId: string): Promise<TeamMember> {
  return request<TeamMember>(`/team-invitations/${encodeURIComponent(invitationId)}/accept`, {
    method: 'POST',
  });
}

export async function revokeTeamInvitation(invitationId: string): Promise<{ message: string }> {
  return request<{ message: string }>(`/team-invitations/${encodeURIComponent(invitationId)}/revoke`, {
    method: 'POST',
  });
}
