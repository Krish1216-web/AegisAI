import { request } from './client';

export interface Project {
  id: string;
  workspace_id: string;
  name: string;
  description?: string | null;
  status: 'active' | 'archived';
  created_by?: string | null;
  created_at: string;
  updated_at: string;
  owner_id?: string | null;
  owner_name?: string | null;
  member_count: number;
  resource_count: number;
}

export interface ProjectListResponse {
  total: number;
  page: number;
  page_size: number;
  projects: Project[];
}

export interface ProjectMember {
  id: string;
  project_id: string;
  user_id: string;
  username: string;
  email: string;
  role: 'owner' | 'editor' | 'viewer';
  status: 'active' | 'removed';
  created_at: string;
  updated_at?: string | null;
}

export interface ProjectMemberListResponse {
  total: number;
  page: number;
  page_size: number;
  members: ProjectMember[];
}

export interface ProjectResource {
  id: string;
  project_id: string;
  workspace_id: string;
  resource_type: 'document' | 'workflow' | 'agent';
  resource_id: string;
  resource_name?: string | null;
  created_by?: string | null;
  created_at: string;
}

export interface ProjectResourceListResponse {
  total: number;
  page: number;
  page_size: number;
  resources: ProjectResource[];
}

export async function getProjects(params?: {
  page?: number;
  page_size?: number;
  status?: string;
  search?: string;
}): Promise<ProjectListResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.append('page', params.page.toString());
  if (params?.page_size) query.append('page_size', params.page_size.toString());
  if (params?.status) query.append('status', params.status);
  if (params?.search) query.append('search', params.search);

  const qStr = query.toString() ? `?${query.toString()}` : '';
  return request<ProjectListResponse>(`/projects${qStr}`);
}

export async function createProject(data: { name: string; description?: string }): Promise<Project> {
  return request<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateProject(id: string, data: { name?: string; description?: string }): Promise<Project> {
  return request<Project>(`/projects/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function archiveProject(id: string): Promise<Project> {
  return request<Project>(`/projects/${encodeURIComponent(id)}/archive`, {
    method: 'POST',
  });
}

export async function restoreProject(id: string): Promise<Project> {
  return request<Project>(`/projects/${encodeURIComponent(id)}/restore`, {
    method: 'POST',
  });
}

export async function transferProjectOwnership(projectId: string, targetUserId: string): Promise<Project> {
  return request<Project>(`/projects/${encodeURIComponent(projectId)}/transfer-ownership`, {
    method: 'POST',
    body: JSON.stringify({ target_user_id: targetUserId }),
  });
}

export async function getProjectMembers(projectId: string, page = 1, pageSize = 50): Promise<ProjectMemberListResponse> {
  return request<ProjectMemberListResponse>(`/projects/${encodeURIComponent(projectId)}/members?page=${page}&page_size=${pageSize}`);
}

export async function addProjectMember(projectId: string, userId: string, role = 'viewer'): Promise<ProjectMember> {
  return request<ProjectMember>(`/projects/${encodeURIComponent(projectId)}/members`, {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, role }),
  });
}

export async function updateProjectMemberRole(projectId: string, userId: string, role: string): Promise<ProjectMember> {
  return request<ProjectMember>(`/projects/${encodeURIComponent(projectId)}/members/${encodeURIComponent(userId)}`, {
    method: 'PUT',
    body: JSON.stringify({ role }),
  });
}

export async function removeProjectMember(projectId: string, userId: string): Promise<void> {
  return request<void>(`/projects/${encodeURIComponent(projectId)}/members/${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  });
}

export async function getProjectResources(projectId: string, page = 1, pageSize = 50, resourceType?: string): Promise<ProjectResourceListResponse> {
  const query = new URLSearchParams({ page: page.toString(), page_size: pageSize.toString() });
  if (resourceType) query.append('resource_type', resourceType);
  return request<ProjectResourceListResponse>(`/projects/${encodeURIComponent(projectId)}/resources?${query.toString()}`);
}

export async function linkProjectResource(projectId: string, resourceType: string, resourceId: string): Promise<ProjectResource> {
  return request<ProjectResource>(`/projects/${encodeURIComponent(projectId)}/resources`, {
    method: 'POST',
    body: JSON.stringify({ resource_type: resourceType, resource_id: resourceId }),
  });
}

export async function unlinkProjectResource(projectId: string, resourceType: string, resourceId: string): Promise<void> {
  return request<void>(`/projects/${encodeURIComponent(projectId)}/resources/${encodeURIComponent(resourceType)}/${encodeURIComponent(resourceId)}`, {
    method: 'DELETE',
  });
}
