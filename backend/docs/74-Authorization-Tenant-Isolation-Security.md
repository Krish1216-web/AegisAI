# 74 — Authorization & Multi-Tenant Isolation Security Architecture

## Executive Summary
AegisAI enforces a zero-trust multi-tenant isolation and unified Role-Based Access Control (RBAC) architecture. Authorization decisions across all platform surfaces—including REST API endpoints, Platform Executions, Real-Time WebSockets/SSE, Knowledge Graphs, Vector/RAG retrievers, MCP tool gateways, and Asynchronous Background Workers—derive tenant identity and user entitlements exclusively from server-side verified sessions rather than client-supplied parameters.

This document details the authorization architecture, permission resolution hierarchy, tenant query isolation rules, IDOR/BOLA mitigations, and security audit verifications completed in Phase 10.3.

---

## 1. Unified Authorization Architecture

### 1.1 The Request Authorization Pipeline
Every stateful request flows through a strict, server-side derivation pipeline:

```
[ Incoming Request (JWT Bearer Token) ]
                 │
                 ▼
[ 1. Authenticate Principal (get_current_user) ]
                 │  - Verify token type: "access"
                 │  - Verify signature & algorithm (HS256)
                 │  - Enforce is_active=True and not is_deleted
                 ▼
[ 2. Resolve Workspace Membership (get_workspace_member) ]
                 │  - Lookup (workspace_id, user_id) in database
                 │  - Reject non-members (403 Forbidden)
                 ▼
[ 3. Resolve Effective Permissions (AuthorizationService) ]
                 │  - Base Workspace Role (Owner, Admin, Member, Viewer)
                 │  + Team Role Overlay (Team Owner / Member)
                 │  + Project Role Overlay (Project Owner / Editor / Viewer)
                 │  + System Admin Override (Platform Admins)
                 ▼
[ 4. Object-Level / IDOR Verification (assert_workspace_ownership) ]
                 │  - Verify target resource.workspace_id == session.workspace_id
                 ▼
[ 5. Execute Authorized Action ]
```

---

## 2. Role & Permission Matrices

### 2.1 Workspace Roles
| Permission Domain | Owner | Admin | Member | Viewer |
|---|---|---|---|---|
| `workspace:view` | ✅ | ✅ | ✅ | ✅ |
| `workspace:update` | ✅ | ✅ | ❌ | ❌ |
| `workspace:members:manage` | ✅ | ✅ | ❌ | ❌ |
| `workspace:roles:manage` | ✅ | ✅ | ❌ | ❌ |
| `workspace:transfer_ownership` | ✅ | ❌ | ❌ | ❌ |
| `document:create / update` | ✅ | ✅ | ✅ | ❌ |
| `document:delete` | ✅ | ✅ | ❌ | ❌ |
| `workflow:execute` | ✅ | ✅ | ✅ | ❌ |
| `workflow:manage` | ✅ | ✅ | ❌ | ❌ |
| `mcp:execute` | ✅ | ✅ | ✅ | ❌ |
| `mcp:manage` | ✅ | ✅ | ❌ | ❌ |
| `collaboration:analytics:view`| ✅ | ✅ | ✅ | ✅ |

### 2.2 Team & Project Role Overlays
- **Team Owner Overlay**: Grants `collaboration:team:manage`, `team:update`, `member:add`, `member:remove`, and `invite:manage` strictly scoped to the team.
- **Project Editor Overlay**: Grants `project:update`, `project:resource:add`, and `project:resource:remove` strictly scoped to the linked project.
- **Boundary Invariant**: Overlays NEVER grant workspace-level administration (`workspace:roles:manage`, `workspace:transfer_ownership`).

---

## 3. Threat Model & Mitigations

| Threat Vector | Attack Scenario | Defensive Control |
|---|---|---|
| **Cross-Tenant IDOR / BOLA** | Attacker probes `UUID` of victim's document or workflow. | `assert_workspace_ownership` & `get_workspace_member` reject mismatched workspace contexts (403/404). |
| **Role Escalation** | Member submits `{"role": "owner"}` in update payload. | Request schemas forbid client-writable role fields; role transitions strictly gated by `Permissions.WORKSPACE_ROLES_MANAGE`. |
| **Owner Demotion / Loss** | Last remaining owner deleted or demoted. | System enforces non-empty owner invariant and atomic `WORKSPACE_TRANSFER_OWNERSHIP`. |
| **Cross-Tenant RAG / Vector Leak** | Semantic query retrieves chunks across workspaces. | Database and vector queries enforce `WHERE workspace_id = :current_ws` filter before retrieval. |
| **Knowledge Graph Traversal Leak** | Graph neighbor expansion walks cross-tenant edge. | All graph nodes and edges are partitioned and filtered by `workspace_id`. |
| **Cross-Tenant MCP Invocation** | Attacker invokes MCP tool registered in another workspace. | MCP dispatcher resolves tools strictly from the authenticated caller's workspace. |
| **Realtime Stream Snooping** | Attacker connects to WebSocket topic of another tenant. | Realtime manager verifies workspace membership before binding topic subscriptions. |
| **Platform Execution Bypass** | Client crafts `SecurityContext` with arbitrary permissions. | `SecurityContext` is created server-side via `AuthorizationService.create_security_context` and enforces `assert_same_tenant`. |

---

## 4. Verification & Dedicated Security Tests

All tenant isolation and authorization invariants are verified in `backend/tests/unit/test_p10_3_authz_tenant_isolation.py`:

- `test_tenant_isolation_cross_workspace_resource_denial`: Cross-workspace access denial and 403 enforcement.
- `test_idor_bola_cross_workspace_probes`: Object-level access verification via `CollaborationResourceAccessService`.
- `test_role_matrix_hierarchy_and_permissions`: Matrix verification for Owner, Admin, Member, Viewer roles.
- `test_team_role_overlay_and_boundaries`: Scoped permission elevation without workspace privilege escalation.
- `test_project_role_overlay_and_boundaries`: Project editor overlay permission validation.
- `test_security_context_tenant_assertion`: Typed `SecurityContext` tenant assertion defense against cross-tenant execution.
- `test_system_admin_universal_access`: Platform admin override across all tenant domains.
- `test_inactive_and_deleted_user_denied_permissions`: Deactivated and soft-deleted accounts blocked from permissions.
- `test_property_fuzz_malformed_client_identifiers`: Boundary resilience against forged, random, or invalid UUIDs.
