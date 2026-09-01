import enum
from typing import Dict, Set, List

class PermissionDomain(str, enum.Enum):
    WORKSPACE = "workspace"
    COLLABORATION = "collaboration"
    PROJECT = "project"
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

    # Project
    PROJECT_VIEW = "project:view"
    PROJECT_CREATE = "project:create"
    PROJECT_UPDATE = "project:update"
    PROJECT_MANAGE = "project:manage"
    PROJECT_ARCHIVE = "project:archive"
    PROJECT_RESTORE = "project:restore"
    PROJECT_MEMBER_VIEW = "project:member:view"
    PROJECT_MEMBER_MANAGE = "project:member:manage"
    PROJECT_RESOURCE_VIEW = "project:resource:view"
    PROJECT_RESOURCE_ADD = "project:resource:add"
    PROJECT_RESOURCE_REMOVE = "project:resource:remove"

    # Comments & Mentions
    COMMENT_VIEW = "collaboration:comment:view"
    COMMENT_CREATE = "collaboration:comment:create"
    COMMENT_UPDATE = "collaboration:comment:update"
    COMMENT_DELETE = "collaboration:comment:delete"
    MENTION_VIEW = "collaboration:mention:view"

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
    Permissions.PROJECT_VIEW,
    Permissions.PROJECT_CREATE,
    Permissions.PROJECT_UPDATE,
    Permissions.PROJECT_MANAGE,
    Permissions.PROJECT_ARCHIVE,
    Permissions.PROJECT_RESTORE,
    Permissions.PROJECT_MEMBER_VIEW,
    Permissions.PROJECT_MEMBER_MANAGE,
    Permissions.PROJECT_RESOURCE_VIEW,
    Permissions.PROJECT_RESOURCE_ADD,
    Permissions.PROJECT_RESOURCE_REMOVE,
    Permissions.COMMENT_VIEW,
    Permissions.COMMENT_CREATE,
    Permissions.COMMENT_UPDATE,
    Permissions.COMMENT_DELETE,
    Permissions.MENTION_VIEW,
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
    "owner": ALL_PERMISSIONS,
    "admin": {
        p for p in ALL_PERMISSIONS if p != Permissions.WORKSPACE_TRANSFER_OWNERSHIP
    },
    "member": {
        Permissions.WORKSPACE_VIEW,
        Permissions.WORKSPACE_MEMBERS_VIEW,
        Permissions.TEAM_VIEW,
        Permissions.MEMBER_VIEW,
        Permissions.PROJECT_VIEW,
        Permissions.PROJECT_CREATE,
        Permissions.PROJECT_MEMBER_VIEW,
        Permissions.PROJECT_RESOURCE_VIEW,
        Permissions.COMMENT_VIEW,
        Permissions.COMMENT_CREATE,
        Permissions.COMMENT_UPDATE,
        Permissions.COMMENT_DELETE,
        Permissions.MENTION_VIEW,
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
        Permissions.PROJECT_VIEW,
        Permissions.PROJECT_MEMBER_VIEW,
        Permissions.PROJECT_RESOURCE_VIEW,
        Permissions.COMMENT_VIEW,
        Permissions.MENTION_VIEW,
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
        Permissions.COMMENT_VIEW,
        Permissions.COMMENT_CREATE,
        Permissions.COMMENT_UPDATE,
        Permissions.COMMENT_DELETE,
    },
    "member": {
        Permissions.TEAM_VIEW,
        Permissions.MEMBER_VIEW,
        Permissions.COMMENT_VIEW,
        Permissions.COMMENT_CREATE,
    }
}

PROJECT_ROLE_OVERLAY: Dict[str, Set[str]] = {
    "owner": {
        Permissions.PROJECT_VIEW,
        Permissions.PROJECT_UPDATE,
        Permissions.PROJECT_MANAGE,
        Permissions.PROJECT_ARCHIVE,
        Permissions.PROJECT_RESTORE,
        Permissions.PROJECT_MEMBER_VIEW,
        Permissions.PROJECT_MEMBER_MANAGE,
        Permissions.PROJECT_RESOURCE_VIEW,
        Permissions.PROJECT_RESOURCE_ADD,
        Permissions.PROJECT_RESOURCE_REMOVE,
        Permissions.COMMENT_VIEW,
        Permissions.COMMENT_CREATE,
        Permissions.COMMENT_UPDATE,
        Permissions.COMMENT_DELETE,
        Permissions.MENTION_VIEW,
    },
    "editor": {
        Permissions.PROJECT_VIEW,
        Permissions.PROJECT_UPDATE,
        Permissions.PROJECT_MEMBER_VIEW,
        Permissions.PROJECT_RESOURCE_VIEW,
        Permissions.PROJECT_RESOURCE_ADD,
        Permissions.PROJECT_RESOURCE_REMOVE,
        Permissions.COMMENT_VIEW,
        Permissions.COMMENT_CREATE,
        Permissions.COMMENT_UPDATE,
        Permissions.COMMENT_DELETE,
        Permissions.MENTION_VIEW,
    },
    "viewer": {
        Permissions.PROJECT_VIEW,
        Permissions.PROJECT_MEMBER_VIEW,
        Permissions.PROJECT_RESOURCE_VIEW,
        Permissions.COMMENT_VIEW,
        Permissions.MENTION_VIEW,
    }
}
