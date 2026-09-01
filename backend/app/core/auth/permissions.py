import enum
from typing import Dict, Set, List

class PermissionDomain(str, enum.Enum):
    WORKSPACE = "workspace"
    COLLABORATION = "collaboration"
    DOCUMENT = "document"
    WORKFLOW = "workflow"
    MCP = "mcp"
    AGENT = "agent"
    ADMIN = "admin"

class Permissions:
    # Workspace
    WORKSPACE_VIEW = "workspace:view"
    WORKSPACE_UPDATE = "workspace:update"
    WORKSPACE_MEMBERS_VIEW = "workspace:members:view"
    WORKSPACE_MEMBERS_MANAGE = "workspace:members:manage"
    WORKSPACE_ROLES_MANAGE = "workspace:roles:manage"
    WORKSPACE_TRANSFER_OWNERSHIP = "workspace:transfer_ownership"

    # Collaboration / Team
    TEAM_VIEW = "collaboration:team:view"
    TEAM_CREATE = "collaboration:team:create"
    TEAM_UPDATE = "collaboration:team:update"
    TEAM_MANAGE = "collaboration:team:manage"
    MEMBER_VIEW = "collaboration:member:view"
    MEMBER_ADD = "collaboration:member:add"
    MEMBER_REMOVE = "collaboration:member:remove"
    INVITE_MANAGE = "collaboration:invite:manage"

    # Document
    DOCUMENT_VIEW = "document:view"
    DOCUMENT_CREATE = "document:create"
    DOCUMENT_UPDATE = "document:update"
    DOCUMENT_DELETE = "document:delete"

    # Workflow
    WORKFLOW_VIEW = "workflow:view"
    WORKFLOW_CREATE = "workflow:create"
    WORKFLOW_EXECUTE = "workflow:execute"
    WORKFLOW_MANAGE = "workflow:manage"

    # MCP
    MCP_VIEW = "mcp:view"
    MCP_EXECUTE = "mcp:execute"
    MCP_MANAGE = "mcp:manage"

    # Admin
    ADMIN_USERS_MANAGE = "admin:users:manage"
    ADMIN_SECURITY_MANAGE = "admin:security:manage"
    ADMIN_ANALYTICS_VIEW = "admin:analytics:view"

ALL_PERMISSIONS: Set[str] = {
    Permissions.WORKSPACE_VIEW,
    Permissions.WORKSPACE_UPDATE,
    Permissions.WORKSPACE_MEMBERS_VIEW,
    Permissions.WORKSPACE_MEMBERS_MANAGE,
    Permissions.WORKSPACE_ROLES_MANAGE,
    Permissions.WORKSPACE_TRANSFER_OWNERSHIP,
    Permissions.TEAM_VIEW,
    Permissions.TEAM_CREATE,
    Permissions.TEAM_UPDATE,
    Permissions.TEAM_MANAGE,
    Permissions.MEMBER_VIEW,
    Permissions.MEMBER_ADD,
    Permissions.MEMBER_REMOVE,
    Permissions.INVITE_MANAGE,
    Permissions.DOCUMENT_VIEW,
    Permissions.DOCUMENT_CREATE,
    Permissions.DOCUMENT_UPDATE,
    Permissions.DOCUMENT_DELETE,
    Permissions.WORKFLOW_VIEW,
    Permissions.WORKFLOW_CREATE,
    Permissions.WORKFLOW_EXECUTE,
    Permissions.WORKFLOW_MANAGE,
    Permissions.MCP_VIEW,
    Permissions.MCP_EXECUTE,
    Permissions.MCP_MANAGE,
    Permissions.ADMIN_USERS_MANAGE,
    Permissions.ADMIN_SECURITY_MANAGE,
    Permissions.ADMIN_ANALYTICS_VIEW,
}

WORKSPACE_ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "owner": {
        Permissions.WORKSPACE_VIEW,
        Permissions.WORKSPACE_UPDATE,
        Permissions.WORKSPACE_MEMBERS_VIEW,
        Permissions.WORKSPACE_MEMBERS_MANAGE,
        Permissions.WORKSPACE_ROLES_MANAGE,
        Permissions.WORKSPACE_TRANSFER_OWNERSHIP,
        Permissions.TEAM_VIEW,
        Permissions.TEAM_CREATE,
        Permissions.TEAM_UPDATE,
        Permissions.TEAM_MANAGE,
        Permissions.MEMBER_VIEW,
        Permissions.MEMBER_ADD,
        Permissions.MEMBER_REMOVE,
        Permissions.INVITE_MANAGE,
        Permissions.DOCUMENT_VIEW,
        Permissions.DOCUMENT_CREATE,
        Permissions.DOCUMENT_UPDATE,
        Permissions.DOCUMENT_DELETE,
        Permissions.WORKFLOW_VIEW,
        Permissions.WORKFLOW_CREATE,
        Permissions.WORKFLOW_EXECUTE,
        Permissions.WORKFLOW_MANAGE,
        Permissions.MCP_VIEW,
        Permissions.MCP_EXECUTE,
        Permissions.MCP_MANAGE,
    },
    "admin": {
        Permissions.WORKSPACE_VIEW,
        Permissions.WORKSPACE_UPDATE,
        Permissions.WORKSPACE_MEMBERS_VIEW,
        Permissions.WORKSPACE_MEMBERS_MANAGE,
        Permissions.WORKSPACE_ROLES_MANAGE,
        Permissions.TEAM_VIEW,
        Permissions.TEAM_CREATE,
        Permissions.TEAM_UPDATE,
        Permissions.TEAM_MANAGE,
        Permissions.MEMBER_VIEW,
        Permissions.MEMBER_ADD,
        Permissions.MEMBER_REMOVE,
        Permissions.INVITE_MANAGE,
        Permissions.DOCUMENT_VIEW,
        Permissions.DOCUMENT_CREATE,
        Permissions.DOCUMENT_UPDATE,
        Permissions.DOCUMENT_DELETE,
        Permissions.WORKFLOW_VIEW,
        Permissions.WORKFLOW_CREATE,
        Permissions.WORKFLOW_EXECUTE,
        Permissions.WORKFLOW_MANAGE,
        Permissions.MCP_VIEW,
        Permissions.MCP_EXECUTE,
        Permissions.MCP_MANAGE,
    },
    "member": {
        Permissions.WORKSPACE_VIEW,
        Permissions.WORKSPACE_MEMBERS_VIEW,
        Permissions.TEAM_VIEW,
        Permissions.MEMBER_VIEW,
        Permissions.DOCUMENT_VIEW,
        Permissions.DOCUMENT_CREATE,
        Permissions.DOCUMENT_UPDATE,
        Permissions.WORKFLOW_VIEW,
        Permissions.WORKFLOW_CREATE,
        Permissions.WORKFLOW_EXECUTE,
        Permissions.MCP_VIEW,
        Permissions.MCP_EXECUTE,
    },
    "viewer": {
        Permissions.WORKSPACE_VIEW,
        Permissions.WORKSPACE_MEMBERS_VIEW,
        Permissions.TEAM_VIEW,
        Permissions.MEMBER_VIEW,
        Permissions.DOCUMENT_VIEW,
        Permissions.WORKFLOW_VIEW,
        Permissions.MCP_VIEW,
    }
}

TEAM_ROLE_OVERLAY: Dict[str, Set[str]] = {
    "owner": {
        Permissions.TEAM_UPDATE,
        Permissions.TEAM_MANAGE,
        Permissions.MEMBER_ADD,
        Permissions.MEMBER_REMOVE,
        Permissions.INVITE_MANAGE,
    },
    "member": {
        Permissions.TEAM_VIEW,
        Permissions.MEMBER_VIEW,
    }
}
