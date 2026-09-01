export const PERMISSIONS = {
  WORKSPACE_VIEW: 'workspace:view',
  WORKSPACE_UPDATE: 'workspace:update',
  WORKSPACE_MEMBERS_VIEW: 'workspace:members:view',
  WORKSPACE_MEMBERS_MANAGE: 'workspace:members:manage',
  WORKSPACE_ROLES_MANAGE: 'workspace:roles:manage',
  WORKSPACE_TRANSFER_OWNERSHIP: 'workspace:transfer_ownership',

  TEAM_VIEW: 'collaboration:team:view',
  TEAM_CREATE: 'collaboration:team:create',
  TEAM_UPDATE: 'collaboration:team:update',
  TEAM_MANAGE: 'collaboration:team:manage',
  MEMBER_VIEW: 'collaboration:member:view',
  MEMBER_ADD: 'collaboration:member:add',
  MEMBER_REMOVE: 'collaboration:member:remove',
  INVITE_MANAGE: 'collaboration:invite:manage',

  DOCUMENT_VIEW: 'document:view',
  DOCUMENT_CREATE: 'document:create',
  DOCUMENT_UPDATE: 'document:update',
  DOCUMENT_DELETE: 'document:delete',

  WORKFLOW_VIEW: 'workflow:view',
  WORKFLOW_CREATE: 'workflow:create',
  WORKFLOW_EXECUTE: 'workflow:execute',
  WORKFLOW_MANAGE: 'workflow:manage',

  MCP_VIEW: 'mcp:view',
  MCP_EXECUTE: 'mcp:execute',
  MCP_MANAGE: 'mcp:manage',

  ADMIN_USERS_MANAGE: 'admin:users:manage',
  ADMIN_SECURITY_MANAGE: 'admin:security:manage',
  ADMIN_ANALYTICS_VIEW: 'admin:analytics:view',
} as const;

export function hasPermission(
  userRole?: string | null,
  effectivePermissions?: string[] | null,
  requiredPermission?: string
): boolean {
  if (!requiredPermission) return true;
  if (userRole === 'admin' || userRole === 'super admin') return true;
  if (!effectivePermissions) return false;
  return effectivePermissions.includes(requiredPermission);
}
