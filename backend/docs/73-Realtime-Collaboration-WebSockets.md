# AegisAI — Phase 9.5: Real-Time Collaboration & WebSockets

## 1. Executive Summary & Architecture
Phase 9.5 introduces the real-time communication layer into AegisAI.
- **WebSocket Gateway**: Authenticated endpoint at `/api/v1/ws`.
- **Authoritative Transport Rule**: WebSockets act strictly as a real-time event synchronization transport. REST APIs and the database remain the authoritative sources of truth.
- **Connection Management**: Centralized singleton `RealtimeConnectionManager` handling thread-safe registration, channel authorization, and message routing.

---

## 2. Authentication & Handshake
- **Protocol**: JWT token provided during WebSocket handshake (`/api/v1/ws?token=<jwt>`).
- **Identity Resolution**: Verified via `decode_token(token)` and database lookup. Client claims of `user_id`, `workspace_id`, or `role` are never trusted.
- **Failure**: Handshake rejection closes the connection immediately with WS code `1008 (Policy Violation)`.

---

## 3. Channel Model & Centralized Authorization
Channels follow explicit scopes:
- `workspace:{workspace_id}` (Auto-subscribed on connection)
- `team:{team_id}`
- `project:{project_id}`

### Authorization Rules:
- **Workspace Scope**: Client can only subscribe to their own authenticated workspace.
- **Team Scope**: Team must belong to client's workspace, and client must be an active team member or workspace owner/admin.
- **Project Scope**: Project must belong to client's workspace, and client must be an active project member or workspace owner/admin.
- Evaluated against `AuthorizationService` and `CollaborationResourceAccessService`.

---

## 4. Immediate Access Revocation
When a user is removed or demoted in a project or team via REST:
1. `ProjectService.remove_member` or `TeamService.remove_team_member` executes.
2. Database state updates.
3. `RealtimeConnectionManager.revoke_user_channel(...)` immediately removes the channel subscription from all active WebSocket connections for that user and sends a `subscription_revoked` notice.
4. Membership change is broadcast to remaining authorized subscribers.

---

## 5. Bounded Connection Limits & Resource Protection
- **Max Connections per User**: 10
- **Max Connections per Workspace**: 200
- **Max Subscriptions per Connection**: 50
- **Max Inbound Message Size**: 65,536 bytes (64 KB)
- **Heartbeat Timeout**: 120 seconds

---

## 6. Presence & Scoped Events
- **Presence States**: `online`, `away`, `offline`.
- **Announcements**: `PRESENCE_JOINED`, `PRESENCE_LEFT`, `PRESENCE_UPDATED`.
- Scoped strictly to the authenticated workspace channels. No cross-tenant presence leakage.

---

## 7. Platform Event Integration
- `RealtimeConnectionManager` subscribes to `PlatformEventDispatcher` on `COLLABORATION_EVENT`.
- Automatically wraps events in `RealtimeEventEnvelope` (`event_id`, `event_type`, `scope`, `workspace_id`, `channel`, `actor_id`, `timestamp`, `correlation_id`, `payload`) and routes to matching channels.

---

## 8. Frontend Real-Time Client & UI
- **Client**: [`frontend/src/api/realtime.ts`](file:///d:/CP/AegisAI/frontend/src/api/realtime.ts)
  - Auto-reconnect with exponential backoff (1s, 2s, 4s, 8s, up to 30s).
  - 30-second ping heartbeat.
  - Event deduplication cache (up to 2,000 recent `event_id`s).
- **UI Integration**:
  - `UserProjects.jsx`: Real-time status indicator badge and automatic live refresh on `PROJECT_RESOURCE_LINKED`, `PROJECT_MEMBER_ADDED`, etc.

---

## 9. Database & Migration Decision
No durable migration was created for Phase 9.5. Ephemeral connection state, heartbeat, and presence are maintained in bounded memory structures. The database migration head remains `016_shared_projects_resources`.

---

## 10. Deferred Features
- **Phase 9.6**: Comments, Mentions & Collaboration Activity
- **Phase 9.7**: Notifications & Real-Time Delivery
- **Phase 9.8**: Collaboration Analytics
- **Phase 9.9**: Security Hardening & Penetration Testing
