# AegisAI — Phase 9.1: Collaboration Foundation

## 1. Executive Summary & Architecture Overview
The AegisAI Collaboration Foundation (Phase 9.1) establishes the multi-tenant collaborative hierarchy that enables multiple users within an organization to organize into teams, manage collaborative resource access, and execute shared workflows without violating tenant isolation.

### The Collaboration Hierarchy
```
                       +---------------------------------------+
                       |              Workspace                |
                       |      (Primary Tenant Boundary)        |
                       +-------------------+-------------------+
                                           |
                                           v
                       +---------------------------------------+
                       |                 Teams                 |
                       |       (Workspace-Scoped Groups)       |
                       +-------------------+-------------------+
                                           |
                                           v
                       +---------------------------------------+
                       |            Team Memberships           |
                       |       (Roles: owner, member)          |
                       +-------------------+-------------------+
                                           |
                                           v
                       +---------------------------------------+
                       |     Collaboration Resource Access     |
                       | (Projects, Workflows, Documents, MCP) |
                       +---------------------------------------+
```

---

## 2. Core Architectural Invariants
1. **Workspace Boundary Strictness**: Teams strictly belong to exactly one workspace (`workspace_id`). Teams can never span multiple workspaces.
2. **Workspace Membership Prerequisite**: A user must be an active member of the workspace before being added to any team inside that workspace.
3. **Identity Provenance**: The caller's workspace identity and user credentials are deterministically resolved server-side via authenticated session context and JWT verification—never trusted from client-supplied payload parameters.
4. **Reversible Migration**: Schema migrations are registered under Alembic revision `014_team_collaboration_foundation` with complete upgrade and downgrade paths.

---

## 3. Team Domain Models & Persistence

### 3.1 Team (`teams` table)
- `id` (UUID, Primary Key)
- `workspace_id` (UUID, Foreign Key to `workspaces.id`, `ON DELETE CASCADE`, Indexed)
- `name` (VARCHAR(100), Unique within workspace)
- `description` (VARCHAR(500), Nullable)
- `status` (VARCHAR(20), Default: `active`, Allowed: `active`, `archived`)
- `created_by` (UUID, Foreign Key to `users.id`, `ON DELETE SET NULL`, Nullable)
- `created_at` (TIMESTAMPTZ, Auto-generated)
- `updated_at` (TIMESTAMPTZ, Nullable)
- **Constraint**: `UNIQUE(workspace_id, name)`

### 3.2 TeamMembership (`team_memberships` table)
- `id` (UUID, Primary Key)
- `team_id` (UUID, Foreign Key to `teams.id`, `ON DELETE CASCADE`, Indexed)
- `user_id` (UUID, Foreign Key to `users.id`, `ON DELETE CASCADE`, Indexed)
- `role` (VARCHAR(50), Default: `member`, Allowed: `owner`, `member`)
- `status` (VARCHAR(20), Default: `active`, Allowed: `active`, `removed`)
- `created_at` (TIMESTAMPTZ, Auto-generated)
- `updated_at` (TIMESTAMPTZ, Nullable)
- **Constraint**: `UNIQUE(team_id, user_id)`

---

## 4. Collaboration Context & Resource Sharing Abstraction

### 4.1 `CollaborationContext`
Encapsulates runtime tenant metadata, caller membership, assigned roles, permissions, and a unique correlation ID:
```python
class CollaborationContext(BaseModel):
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    team_id: Optional[uuid.UUID] = None
    membership_id: Optional[uuid.UUID] = None
    permissions: Set[str] = Field(default_factory=set)
    correlation_id: str
```

### 4.2 `CollaborationResourceAccessService`
Provides centralized access evaluation for any collaborative resource:
- Verifies that the user is an active member of the target workspace.
- Verifies that the team is active within the workspace.
- Verifies that the user has an active membership within the specified team.

---

## 5. REST API Reference

All endpoints are mounted under `/api/v1/teams`:

| Method | Endpoint | Description | Auth & Permission Required |
|---|---|---|---|
| `POST` | `/api/v1/teams` | Create a new team in active workspace | Authenticated workspace member |
| `GET` | `/api/v1/teams` | List teams with pagination and filters | Authenticated workspace member |
| `GET` | `/api/v1/teams/{team_id}` | Get team details and member count | Authenticated workspace member |
| `PUT` | `/api/v1/teams/{team_id}` | Update team name and description | Team owner / Workspace admin |
| `POST` | `/api/v1/teams/{team_id}/archive` | Archive team | Team owner / Workspace admin |
| `GET` | `/api/v1/teams/{team_id}/members` | List active team members | Authenticated workspace member |
| `POST` | `/api/v1/teams/{team_id}/members` | Add a workspace member to the team | Team owner / Workspace admin |
| `DELETE` | `/api/v1/teams/{team_id}/members/{user_id}` | Remove a member from the team | Team owner / Workspace admin |

---

## 6. Audit & Platform Event Integration
Every team lifecycle operation generates immutable audit records and platform events:
- `TEAM_CREATED`: Recorded when a new team is spawned. Creator is automatically assigned the `owner` role.
- `TEAM_UPDATED`: Recorded when team metadata is modified.
- `TEAM_ARCHIVED`: Recorded when a team status transitions to `archived`.
- `TEAM_MEMBER_ADDED`: Recorded when a user is granted team membership.
- `TEAM_MEMBER_REMOVED`: Recorded when a membership status is set to `removed`.

Sensitive tokens and keys in metadata are automatically scrubbed via `CredentialStore`.

---

## 7. Frontend User Management Console
Located at [`frontend/src/pages/user/UserTeams.jsx`](file:///d:/CP/AegisAI/frontend/src/pages/user/UserTeams.jsx):
- **Live Directory**: Searchable, paginated list of active and archived teams.
- **Team Inspector**: Side-by-side view displaying team status, metadata, and full membership roster.
- **Member Management**: Add and remove members with instant UI updates and confirmation modals.
- **Safe Rendering**: No `eval()`, no `exec()`, no `dangerouslySetInnerHTML`.

---

## 8. Deferred Phase 9 Features
The following capabilities are planned for subsequent Phase 9 milestones and are intentionally decoupled from Phase 9.1:
- **Phase 9.2**: Extended Teams & Advanced Membership Management
- **Phase 9.3**: Granular Role & Workspace Permissions Matrix
- **Phase 9.4**: Shared Projects & Resource Collections
- **Phase 9.5**: Real-Time Collaboration & WebSockets
- **Phase 9.6**: Comments, Mentions & Collaboration Activity Feeds
- **Phase 9.7**: Collaboration Notifications & Webhooks
- **Phase 9.8**: Team Collaboration Analytics & Insights
- **Phase 9.9**: End-to-End Security Hardening & Penetration Testing
