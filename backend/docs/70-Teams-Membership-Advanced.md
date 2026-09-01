# AegisAI — Phase 9.2: Advanced Teams & Membership

## 1. Executive Summary & Architecture Overview
Phase 9.2 extends the AegisAI collaboration foundation with production-grade team management, robust membership lifecycles, cryptographic invitation workflows, atomic team ownership transfer with owner removal protection, and workspace-scoped eligible member discovery.

---

## 2. Advanced Team Management
- **Archival & Restoration**: Teams can transition between `active` and `archived` statuses. Restoring an archived team validates name uniqueness against current active teams within the workspace (`POST /api/v1/teams/{team_id}/restore`).
- **Owner Resolution**: Team responses enrich primary owner identity (`owner_id`, `owner_name`) alongside real-time active member counts.

---

## 3. Robust Ownership Management & Protection
- **Atomic Ownership Transfer**: `POST /api/v1/teams/{team_id}/transfer-ownership` transitions the target active team member to `owner` and demotes existing owner(s) to `member` within an atomic database transaction.
- **Owner Removal Protection**: Attempting to remove the sole active owner of a team returns `400 Bad Request` (`"Cannot remove the sole team owner. Transfer ownership before removal."`).

---

## 4. Membership Lifecycle & Safe Reactivation
- **States**: `active` and `removed`.
- **Safe Reactivation**: Adding a previously removed user reactivates their existing membership record rather than triggering unique constraint violations (`UNIQUE(team_id, user_id)`), logging `TEAM_MEMBERSHIP_REACTIVATED`.

---

## 5. Team Invitation System & Security

### 5.1 TeamInvitation Data Model (`team_invitations` table)
- `id` (UUID, Primary Key)
- `team_id` (UUID, FK to `teams.id`, `ON DELETE CASCADE`, Indexed)
- `workspace_id` (UUID, FK to `workspaces.id`, `ON DELETE CASCADE`, Indexed)
- `invited_user_id` (UUID, FK to `users.id`, `ON DELETE CASCADE`, Nullable, Indexed)
- `invited_email` (VARCHAR(255), Nullable, Indexed)
- `invited_by` (UUID, FK to `users.id`, `ON DELETE SET NULL`, Nullable)
- `token_hash` (VARCHAR(64), Nullable, Indexed)
- `role` (VARCHAR(50), Default: `member`)
- `status` (VARCHAR(20), Default: `pending`, Allowed: `pending`, `accepted`, `expired`, `revoked`, Indexed)
- `expires_at` (TIMESTAMPTZ, Indexed)
- `accepted_at` (TIMESTAMPTZ, Nullable)

### 5.2 Token Cryptography
- Secrets are generated using `secrets.token_urlsafe(32)`.
- Stored exclusively as SHA-256 hashes (`token_hash = hashlib.sha256(raw_token).hexdigest()`).
- Raw tokens are never logged or exposed in responses.

### 5.3 Acceptance & Revocation Flow
- `POST /api/v1/teams/{team_id}/invitations`: Issues a workspace-scoped invitation.
- `GET /api/v1/teams/{team_id}/invitations`: Lists team invitations with pagination and status filters.
- `POST /api/v1/team-invitations/{invitation_id}/accept`: Accepts invitation, validates user identity and workspace boundary, activates/reactivates membership, and sets status to `accepted`.
- `POST /api/v1/team-invitations/{invitation_id}/revoke`: Revokes a pending invitation.

---

## 6. Member Discovery
`GET /api/v1/teams/{team_id}/eligible-members` enables team managers to search and discover workspace members who are not currently active in the team, returning sanitized non-sensitive user metadata (`user_id`, `username`, `email`, `workspace_role`).

---

## 7. Audit & Platform Events
All Phase 9.2 actions produce immutable audit logs and platform events:
- `TEAM_RESTORED`
- `TEAM_OWNER_TRANSFERRED`
- `TEAM_INVITATION_CREATED`
- `TEAM_INVITATION_ACCEPTED`
- `TEAM_INVITATION_REVOKED`
- `TEAM_MEMBERSHIP_REACTIVATED`

---

## 8. Frontend Experience
Implemented in [`frontend/src/pages/user/UserTeams.jsx`](file:///d:/CP/AegisAI/frontend/src/pages/user/UserTeams.jsx):
- Restore action for archived teams.
- Ownership crown badge and Transfer Ownership modal.
- Tabbed view: "Active Members" and "Invitations".
- Eligible Member picker in Invitation modal with instant search.
- Revoke button for pending invitations.
- Safe rendering: zero `eval()`, zero `exec()`, zero `dangerouslySetInnerHTML`.

---

## 9. Database Migration
Registered in [`backend/alembic/versions/015_team_invitations.py`](file:///d:/CP/AegisAI/backend/alembic/versions/015_team_invitations.py), upgrading from `014_team_collaboration_foundation` to `015_team_invitations`.

---

## 10. Deferred Phase 9 Features
- **Phase 9.3**: Roles & Workspace Permissions Matrix
- **Phase 9.4**: Shared Projects & Resources
- **Phase 9.5**: Real-Time Collaboration & WebSockets
- **Phase 9.6**: Comments, Mentions & Collaboration Activity
- **Phase 9.7**: Notifications & Real-Time Delivery
- **Phase 9.8**: Collaboration Analytics
- **Phase 9.9**: Security Hardening & Penetration Testing
