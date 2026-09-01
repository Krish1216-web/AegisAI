import { request } from './client';

export interface CommentMention {
  user_id: string;
  username: string;
}

export interface CommentItem {
  id: string;
  workspace_id: string;
  author_id?: string | null;
  author_name: string;
  project_id?: string | null;
  resource_type?: string | null;
  resource_id?: string | null;
  parent_comment_id?: string | null;
  body: string;
  status: 'active' | 'deleted';
  created_at: string;
  updated_at: string;
  edited_at?: string | null;
  deleted_at?: string | null;
  reply_count: number;
  mentions: CommentMention[];
}

export interface CommentListResponse {
  total: number;
  page: number;
  page_size: number;
  comments: CommentItem[];
}

export interface MentionableUser {
  user_id: string;
  username: string;
  email: string;
}

export interface ActivityItem {
  id: string;
  activity_type: string;
  description: string;
  user_id?: string | null;
  username?: string | null;
  created_at: string;
}

export interface ActivityListResponse {
  total: number;
  page: number;
  page_size: number;
  activities: ActivityItem[];
}

export async function getComments(params?: {
  project_id?: string;
  resource_type?: string;
  resource_id?: string;
  parent_comment_id?: string;
  page?: number;
  page_size?: number;
}): Promise<CommentListResponse> {
  const query = new URLSearchParams();
  if (params?.project_id) query.append('project_id', params.project_id);
  if (params?.resource_type) query.append('resource_type', params.resource_type);
  if (params?.resource_id) query.append('resource_id', params.resource_id);
  if (params?.parent_comment_id) query.append('parent_comment_id', params.parent_comment_id);
  if (params?.page) query.append('page', params.page.toString());
  if (params?.page_size) query.append('page_size', params.page_size.toString());

  const qStr = query.toString() ? `?${query.toString()}` : '';
  return request<CommentListResponse>(`/comments${qStr}`);
}

export async function createComment(data: {
  body: string;
  project_id?: string;
  resource_type?: string;
  resource_id?: string;
  parent_comment_id?: string;
}): Promise<CommentItem> {
  return request<CommentItem>('/comments', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateComment(commentId: string, body: string): Promise<CommentItem> {
  return request<CommentItem>(`/comments/${encodeURIComponent(commentId)}`, {
    method: 'PUT',
    body: JSON.stringify({ body }),
  });
}

export async function deleteComment(commentId: string): Promise<void> {
  return request<void>(`/comments/${encodeURIComponent(commentId)}`, {
    method: 'DELETE',
  });
}

export async function getMentionableUsers(projectId: string, search?: string): Promise<MentionableUser[]> {
  const query = search ? `?search=${encodeURIComponent(search)}` : '';
  return request<MentionableUser[]>(`/projects/${encodeURIComponent(projectId)}/mentionable-users${query}`);
}

export async function getProjectActivity(projectId: string, page = 1, pageSize = 50): Promise<ActivityListResponse> {
  return request<ActivityListResponse>(`/projects/${encodeURIComponent(projectId)}/activity?page=${page}&page_size=${pageSize}`);
}
