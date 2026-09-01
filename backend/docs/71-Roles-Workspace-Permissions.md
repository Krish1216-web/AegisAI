# AegisAI — Phase 9.3: Roles & Workspace Permissions

## 1. Executive Summary & Architecture
Phase 9.3 establishes a production-grade, unified authorization model for AegisAI. It integrates system roles, workspace roles, and team roles into a single authoritative permission engine (`AuthorizationService`), preventing fragmented role checks and privilege escalation vulnerabilities.

---

## 2. Existing RBAC Architecture & Unified Model
- **System Roles**: `admin`, `user` (configured on `users.role_id`).
- **Workspace Roles**: `owner`, `admin`, `member`, `viewer` (configured on `workspace_members.role`).
- **Team Roles**: `owner`, `member` (configured on `team_memberships.role`).
- **Authorization Engine**: `AuthorizationService` (`backend/app/services/authorization.py`) computes deterministic effective permission sets based on the unified hierarchy.

---

## 3. Permission Model & Domain Catalog
Defined in `backend/app/core/auth/permissions.py`:
- **Workspace**: `workspace:view`, `workspace:update`, `workspace:members:view`, `workspace:members:manage`, `workspace:roles:manage`, `workspace:transfer_ownership`
- **Collaboration / Team**: `collaboration:team:view`, `collaboration:team:create`, `collaboration:team:update`, `collaboration:team:manage`, `collaboration:member:view`, `collaboration:member:add`, `collaboration:member:remove`, `collaboration:invite:manage`
- **Document**: `document:view`, `document:create`, `document:update`, `document:delete`
- **Workflow**: `workflow:view`, `workflow:create`, `workflow:execute`, `workflow:manage`
- **MCP**: `mcp:view`, `mcp:execute`, `mcp:manage`
- **Admin**: `admin:users:manage`, `admin:security:manage`, `admin:analytics:view`

---

## 4. Role-to-Permission Mapping Matrix

| Permission | Owner | Admin | Member | Viewer |
|---|---|---|---|---|
| `workspace:view` | ✅ | ✅ | ✅ | ✅ |
| `workspace:update` | ✅ | ✅ | ❌ | ❌ |
| `workspace:members:view` | ✅ | ✅ | ✅ | ✅ |
| `workspace:members:manage` | ✅ | ✅ | ❌ | ❌ |
| `workspace:roles:manage` | ✅ | ✅ | ❌ | ❌ |
| `workspace:transfer_ownership` | ✅ | ❌ | ❌ | ❌ |
| `collaboration:team:create` | ✅ | ✅ | ❌ | ❌ |
| `collaboration:team:manage` | ✅ | ✅ | ❌ (Team Owner only) | ❌ |
| `document:create` | ✅ | ✅ | ✅ | ❌ |
| `workflow:execute` | ✅ | ✅ | ✅ | ❌ |
| `mcp:execute` | ✅ | ✅ | ✅ | ❌ |

---

## 5. Team Role Overlay
Team membership augments a user's permissions within the team's scope without escalating workspace-wide authority:
- **Team Owner**: Adds `collaboration:team:update`, `collaboration:team:manage`, `collaboration:member:add`, `collaboration:member:remove`, `collaboration:invite:manage`.
- **Team Member**: Standard team collaboration within the team.

---

## 6. Workspace Role Management & Ownership Protection
- **Role Updates**: `PUT /api/v1/workspaces/{workspace_id}/members/{user_id}/role` validates actor authority and prevents demoting the sole workspace owner.
- **Ownership Transfer**: `POST /api/v1/workspaces/{workspace_id}/transfer-ownership` transitions existing owner(s) to `admin` and grants `owner` role to target member atomically.
- **Sole Owner Removal Defense**: Attempting to delete the sole workspace owner returns `400 Bad Request`.

---

## 7. REST APIs
- `GET /api/v1/workspaces/{workspace_id}/members`: Paginated member directory.
- `PUT /api/v1/workspaces/{workspace_id}/members/{user_id}/role`: Workspace role update.
- `POST /api/v1/workspaces/{workspace_id}/transfer-ownership`: Atomic ownership transfer.
- `GET /api/v1/workspaces/{workspace_id}/effective-permissions`: Inspect caller permissions.
- `GET /api/v1/permissions`: Permissions registry and role mapping matrix.

---

## 8. Frontend Integration
- **Utility**: [`frontend/src/utils/permissions.ts`](file:///d:/CP/AegisAI/frontend/src/utils/permissions.ts) with `hasPermission(role, effectivePermissions, permission)`.
- **API Client**: [`frontend/src/api/workspaces.ts`](file:///d:/CP/AegisAI/frontend/src/api/workspaces.ts).

---

## 9. Audit & Platform Events
- `WORKSPACE_ROLE_CHANGED`
- `WORKSPACE_OWNER_TRANSFERRED`
- `WORKSPACE_MEMBER_ADDED`

---

## 10. Database & Migration
Zero schema migration required. Existing `WorkspaceMember.role`, `TeamMembership.role`, and `User.role_id` relational schemas natively support the unified authorization model. Alembic head remains `015_team_invitations`.

---

## 11. Deferred Features
- **Phase 9.4**: Shared Projects & Resources
- **Phase 9.5**: Real-Time Collaboration & WebSockets
- **Phase 9.6**: Comments, Mentions & Collaboration Activity
- **Phase 9.7**: Notifications & Real-Time Delivery
- **Phase 9.8**: Collaboration Analytics
- **Phase 9.9**: Security Hardening & Penetration Testing
