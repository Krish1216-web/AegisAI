# AegisAI — Phase 9.6: Comments, Mentions & Collaboration Activity

## 1. Executive Summary & Architecture
Phase 9.6 establishes the persistent human collaboration layer in AegisAI:
- **Comments**: Scoped to projects or shared resources (documents, workflows, agents).
- **Threading**: Lightweight hierarchy using `parent_comment_id` with circular prevention and depth limits (`MAX_COMMENT_DEPTH = 10`).
- **Mentions**: Deterministic `@username` extraction, storage in `comment_mentions`, and scoped mentionable user directory.
- **Activity Timeline**: User-facing collaboration activity log distinct from security `AuditLog`.
- **Real-Time Integration**: Emits `COMMENT_CREATED`, `COMMENT_UPDATED`, `COMMENT_DELETED`, `MENTION_CREATED` events over the Phase 9.5 WebSocket gateway.

---

## 2. Domain Models & Database Migration
- **Table `comments`**:
  - `id`: UUID (PK)
  - `workspace_id`: UUID (FK `workspaces.id`, ondelete='CASCADE', indexed)
  - `author_id`: UUID (FK `users.id`, ondelete='SET NULL', indexed)
  - `project_id`: Optional[UUID] (FK `projects.id`, ondelete='CASCADE', indexed)
  - `resource_type`: Optional[str] (VARCHAR(50), indexed) — `document`, `workflow`, `agent`
  - `resource_id`: Optional[str] (VARCHAR(255), indexed)
  - `parent_comment_id`: Optional[UUID] (FK `comments.id`, ondelete='CASCADE', indexed)
  - `body`: Text (1..10,000 characters)
  - `status`: VARCHAR(20) (`active`, `deleted`)
  - `created_at`, `updated_at`, `edited_at`, `deleted_at`
- **Table `comment_mentions`**:
  - `id`: UUID (PK)
  - `comment_id`: UUID (FK `comments.id`, ondelete='CASCADE', indexed)
  - `mentioned_user_id`: UUID (FK `users.id`, ondelete='CASCADE', indexed)
  - `created_at`: TIMESTAMPTZ
  - `UNIQUE(comment_id, mentioned_user_id)`
- **Migration**: `017_comments_mentions.py` (down revision `016_shared_projects_resources`).

---

## 3. Permissions & Centralized Authorization
Added to `backend/app/core/auth/permissions.py`:
- `collaboration:comment:view`
- `collaboration:comment:create`
- `collaboration:comment:update`
- `collaboration:comment:delete`
- `collaboration:mention:view`

Enforced across `WORKSPACE_ROLE_PERMISSIONS`, `PROJECT_ROLE_OVERLAY`, and `TEAM_ROLE_OVERLAY`.

---

## 4. Mention Parsing & Security
- **Parsing**: Regex pattern `r'(?<!\w)@([a-zA-Z0-9_.-]{1,50})'` extracts unique usernames without dynamic evaluation.
- **Directory Isolation**: `/api/v1/projects/{project_id}/mentionable-users` only returns active users who are members of the current workspace and project.
- **Cross-Tenant Defense**: Cross-tenant users cannot be mentioned or resolved.

---

## 5. Soft-Deletion & Thread Preservation
- When deleted via `DELETE /api/v1/comments/{id}`, the comment is marked `status = "deleted"` and `deleted_at = now()`.
- Public listing masks deleted content as `"This comment was deleted."`, preserving reply tree hierarchy.

---

## 6. AuditLog vs ActivityLog
- `AuditLog`: Security and compliance records (`COMMENT_CREATED`, `COMMENT_DELETED`).
- `ActivityLog`: User-facing collaboration timeline (`COMMENT_CREATED`, etc.) accessible via `/api/v1/projects/{project_id}/activity`.

---

## 7. Real-Time WebSocket Synchronization
Emits `COLLABORATION_EVENT` via `PlatformEventDispatcher`, which `RealtimeConnectionManager` routes to project/workspace subscribers:
- `COMMENT_CREATED`
- `COMMENT_UPDATED`
- `COMMENT_DELETED`
- `MENTION_CREATED`

---

## 8. Frontend Collaboration Experience
- **Client**: `frontend/src/api/comments.ts`
- **Component**: `frontend/src/components/collaboration/CommentsPanel.jsx` (threaded views, inline reply composer, edit/delete actions, plain text rendering).
- **UI Pages**: `frontend/src/pages/user/UserProjects.jsx` (Comments and Activity tabs).

---

## 9. Deferred Features
- **Phase 9.7**: Notifications & Real-Time Delivery (Email, Push, Center, Preferences).
- **Phase 9.8**: Collaboration Analytics.
- **Phase 9.9**: Security Hardening & Penetration Testing.
