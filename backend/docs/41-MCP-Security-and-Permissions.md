# AegisAI — Phase 6.6: MCP Security & Permissions

## 1. Executive Summary

Phase 6.6 establishes the centralized, tenant-isolated MCP Security & Permissions control plane for AegisAI. The security layer enforces a deterministic evaluation pipeline across all Model Context Protocol assets (servers, tools, resources, prompts, and tool executions). All external content is strictly classified and stamped with `UNTRUSTED_MCP` trust labels, preventing prompt injections, SSRF, command execution tampering, and system instruction overrides while providing enterprise-grade capability-level RBAC, single-use confirmation gating, and secret-redacted audit event logging.

---

## 2. Security Control Plane Architecture

```
                    MCP PLATFORM REQUEST
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
          TOOLS          RESOURCES         PROMPTS
            │                │                │
            └────────────────┼────────────────┘
                             │
                             ▼
               ┌───────────────────────────┐
               │    MCPSecurityService     │
               └─────────────┬─────────────┘
                             │
      ┌──────────────────────┼──────────────────────┐
      │                      │                      │
1. Identity / Auth     2. Tenant Scope       3. Workspace Membership
      │                      │                      │
4. Server Status       5. Capability Status  6. Capability RBAC
      │                      │                      │
7. Risk Policy         8. Confirmation Token 9. Rate Limits
      │                      │                      │
      └──────────────────────┼──────────────────────┘
                             │
                             ▼
                    Deterministic Decision
                  (ALLOW / CONFIRM / DENY)
                             │
                             ▼
               ┌───────────────────────────┐
               │ Structured Audit Logging  │
               │ (No secrets / credentials)│
               └───────────────────────────┘
```

---

## 3. Decision Model & Precedence Pipeline

Decisions are rendered by `MCPSecurityService` ([`backend/app/services/mcp/mcp_security.py`](file:///d:/CP/AegisAI/backend/app/services/mcp/mcp_security.py)) with strict precedence:

| Priority | Evaluation Stage | Failure Reason Code | Outcome |
| :---: | :--- | :--- | :---: |
| **1** | User Authentication & Active Account | `AUTHENTICATION_REQUIRED` | `DENY` |
| **2** | Workspace Membership Verification | `WORKSPACE_ACCESS_DENIED` | `DENY` |
| **3** | Server Ownership & Tenant Isolation | `TENANT_MISMATCH` | `DENY` |
| **4** | Server Status & Enabled State | `SERVER_DISABLED` / `SERVER_INACTIVE` | `DENY` |
| **5** | Capability Status & Stale Detection | `CAPABILITY_DISABLED` / `CAPABILITY_STALE` | `DENY` |
| **6** | Capability-Level RBAC Permission | `RBAC_DENIED` | `DENY` |
| **7** | Risk Assessment (`ToolRiskPolicy`) | `RISK_POLICY_DENIED` | `DENY` (if `INVALID`) |
| **8** | Confirmation Gating (`RESTRICTED` tools) | `CONFIRMATION_REQUIRED` / `CONFIRMATION_INVALID` | `REQUIRE_CONFIRMATION` / `DENY` |
| **9** | Passed All Policies | `SUCCESS` | `ALLOW` |

---

## 4. Capability-Level RBAC Permissions

| Permission Name | Category | Scope | User Role | Admin Role |
| :--- | :--- | :--- | :---: | :---: |
| `mcp:server:view` | Server | View registered MCP servers | Granted | Granted |
| `mcp:server:manage` | Server | Register, edit, toggle, delete servers | Denied | Granted |
| `mcp:tool:view` | Tool | View tool schemas & catalogs | Granted | Granted |
| `mcp:tool:execute` | Tool | Execute approved MCP tools | Granted | Granted |
| `mcp:tool:manage` | Tool | Toggle tool availability | Denied | Granted |
| `mcp:resource:view` | Resource | View discovered resources | Granted | Granted |
| `mcp:resource:read` | Resource | Read sanitized resource content | Granted | Granted |
| `mcp:resource:manage` | Resource | Toggle resource availability | Denied | Granted |
| `mcp:prompt:view` | Prompt | View discovered prompt templates | Granted | Granted |
| `mcp:prompt:render` | Prompt | Render prompt templates with arguments | Granted | Granted |
| `mcp:prompt:manage` | Prompt | Toggle prompt availability | Denied | Granted |

---

## 5. Security & Trust Boundaries

1. **Content Trust Labels (`UNTRUSTED_MCP`)**:
   - All tool descriptions, tool execution outputs, prompt templates, and resource contents are marked as `UNTRUSTED_MCP`.
   - External prompt messages labeled with role `"system"` are normalized and prohibited from overriding AegisAI system prompts.
2. **Single-Use Cryptographic Confirmation Tokens**:
   - Gating mechanism for `RESTRICTED` tools.
   - Bound to `SHA256(user_id:workspace_id:tool_id:args_hash:uuid)` with strict single-use consumption.
3. **SSRF & Network Hardening**:
   - Blocks private/loopback IP addresses (`127.0.0.1`, `0.0.0.0`, `10.0.0.0/8`, `192.168.0.0/16`, `172.16.0.0/12`), AWS metadata (`169.254.169.254`), and `file://` URIs.
4. **Structured Security Auditing**:
   - Emits structured events (`MCP_ACCESS_ALLOWED`, `MCP_ACCESS_DENIED`, `MCP_PERMISSION_DENIED`, `MCP_TENANT_DENIED`, `MCP_CONFIRMATION_REQUIRED`, `MCP_SECURITY_VIOLATION`).
   - Automatically redacts API keys, tokens, authorization headers, and sensitive payload dictionaries.

---

## 6. REST APIs

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/mcp/security/status` | Returns workspace security metrics, active RBAC permissions, and policy status. |
| `GET` | `/api/v1/mcp/security/audit-log` | Retrieves recent security audit events with redacted metadata. |

---

## 7. Verification Matrix

- **Backend Unit Tests**: **279 / 279 passing (100%)**
  ```bash
  pytest tests/unit/ -v
  ====================== 279 passed, 57 warnings in 48.93s ======================
  ```
- **Frontend Production Build**: **Clean Vite build in 1.91s**
  ```bash
  npm run build
  ✓ built in 1.91s
  ```
- **Database Migration**: Reused migration head `010_mcp_advanced_discovery (head)` (zero redundant migrations).
- **Git Branch**: `phase-6-mcp-platform`
