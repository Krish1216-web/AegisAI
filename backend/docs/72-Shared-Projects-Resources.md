# AegisAI — Phase 9.4: Shared Projects & Resources

## 1. Executive Summary & Architecture Overview
Phase 9.4 establishes the collaborative resource layer in AegisAI. It enables workspace-scoped projects, project membership with granular project-level roles (`owner`, `editor`, `viewer`), and collaborative resource linking for Documents, Workflows, and Agents.

---

## 2. Project Domain Model
- **Table**: `projects` (`backend/app/models/project.py`)
- **Fields**: `id`, `workspace_id`, `name`, `description`, `status` (`active`, `archived`), `created_by`, `created_at`, `updated_at`.
- **Constraint**: `UNIQUE(workspace_id, name)`.
- **Lifecycle**:
  - `active`: Normal mutations, member and resource additions allowed.
  - `archived`: Read-only historical state; can be restored via `POST /api/v1/projects/{project_id}/restore`.

---

## 3. Project Membership & Roles
- **Table**: `project_memberships`
- **Fields**: `id`, `project_id`, `user_id`, `role` (`owner`, `editor`, `viewer`), `status` (`active`, `removed`), `created_at`, `updated_at`.
- **Constraint**: `UNIQUE(project_id, user_id)`.
- **Roles**:
  - `owner`: Full project management, member administration, resource linking/unlinking, archive/restore, and ownership transfer.
  - `editor`: Resource linking/unlinking and collaborative project editing.
  - `viewer`: Read-only access to project overview, members, and linked resources.
- **Reactivation**: Adding a previously removed member reactivates their record safely without unique constraint errors.
- **Owner Protection**: Sole project owner cannot be removed or demoted without explicit ownership transfer (`POST /api/v1/projects/{project_id}/transfer-ownership`).

---

## 4. Resource Sharing & Preservation of Ownership
- **Table**: `project_resources`
- **Supported Resource Types**: `document`, `workflow`, `agent`.
- **Constraint**: `UNIQUE(project_id, resource_type, resource_id)`.
- **Ownership Preservation**: Linking a document or workflow to a project does NOT change the underlying author/owner. Unlinking a resource from a project removes the project association without deleting the underlying entity.
- **Workspace Boundary**: Resource linking strictly validates that the referenced resource exists within the same workspace. Cross-tenant resource linking is rejected with `404 Not Found`.

---

## 5. Centralized Authorization Integration
- **Overlay**: `PROJECT_ROLE_OVERLAY` in `backend/app/core/auth/permissions.py`.
- **Calculation**: `AuthorizationService.get_effective_permissions(user_id, workspace_id, project_id=...)` overlays project permissions onto workspace authority.
- **Access Check**: `CollaborationResourceAccessService.check_access(...)` validates workspace boundary, project membership, and resource linkage.

---

## 6. REST API Reference
- `POST   /api/v1/projects`: Create project
- `GET    /api/v1/projects`: List projects (with search, pagination, status filter)
- `GET    /api/v1/projects/{project_id}`: Get project details
- `PUT    /api/v1/projects/{project_id}`: Update project metadata
- `POST   /api/v1/projects/{project_id}/archive`: Archive project
- `POST   /api/v1/projects/{project_id}/restore`: Restore project
- `POST   /api/v1/projects/{project_id}/transfer-ownership`: Transfer project ownership
- `GET    /api/v1/projects/{project_id}/members`: List project members
- `POST   /api/v1/projects/{project_id}/members`: Add project member
- `PUT    /api/v1/projects/{project_id}/members/{user_id}`: Update project member role
- `DELETE /api/v1/projects/{project_id}/members/{user_id}`: Remove project member
- `GET    /api/v1/projects/{project_id}/resources`: List linked resources
- `POST   /api/v1/projects/{project_id}/resources`: Link resource
- `DELETE /api/v1/projects/{project_id}/resources/{resource_type}/{resource_id}`: Unlink resource

---

## 7. Frontend Project Experience
- **Page**: [`frontend/src/pages/user/UserProjects.jsx`](file:///d:/CP/AegisAI/frontend/src/pages/user/UserProjects.jsx)
- **Client**: [`frontend/src/api/projects.ts`](file:///d:/CP/AegisAI/frontend/src/api/projects.ts)
- **Features**: Project search, status filter, creation modal, tabbed views for members and resources, resource linking modal, and unlinking actions.

---

## 8. Audit & Platform Events
- `PROJECT_CREATED`
- `PROJECT_UPDATED`
- `PROJECT_ARCHIVED`
- `PROJECT_RESTORED`
- `PROJECT_MEMBER_ADDED`
- `PROJECT_MEMBER_REMOVED`
- `PROJECT_MEMBER_ROLE_CHANGED`
- `PROJECT_OWNER_TRANSFERRED`
- `PROJECT_RESOURCE_LINKED`
- `PROJECT_RESOURCE_UNLINKED`

---

## 9. Database Migration
Registered in [`backend/alembic/versions/016_shared_projects_resources.py`](file:///d:/CP/AegisAI/backend/alembic/versions/016_shared_projects_resources.py), upgraded from `015_team_invitations` to `016_shared_projects_resources`.

---

## 10. Deferred Features
- **Phase 9.5**: Real-Time Collaboration & WebSockets
- **Phase 9.6**: Comments, Mentions & Collaboration Activity
- **Phase 9.7**: Notifications & Real-Time Delivery
- **Phase 9.8**: Collaboration Analytics
- **Phase 9.9**: Security Hardening & Penetration Testing
