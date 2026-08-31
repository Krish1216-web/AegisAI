# Phase 6.9: MCP Security Threat Model & Attack Surface Analysis

## Overview
This document defines the comprehensive Security Threat Model for the Model Context Protocol (MCP) subsystem within AegisAI. It enumerates threats, attack vectors, trust boundaries, impact assessments, and architectural mitigations across all capability types (Tools, Resources, Prompts, Transports, and Multi-Agent interactions).

---

## 1. Trust Boundaries & Assumptions

```
+-----------------------------------------------------------------------------------+
|                            TRUSTED AEGIS CORE LAYER                              |
|  - PostgreSQL Database (Authenticated RBAC & Tenant Workspaces)                   |
|  - LangGraph Multi-Agent Engine (Orchestrator, Planner, Critic, ResponseGen)     |
|  - MCPSecurityService (Precedence Gate, Permission Check, Audit Logger)           |
+-----------------------------------------------------------------------------------+
                                         │
                   ══════════════════════╪══════════════════════
                                  TRUST BOUNDARY
                   ══════════════════════╪══════════════════════
                                         ▼
+-----------------------------------------------------------------------------------+
|                           UNTRUSTED MCP EXTERNAL LAYER                            |
|  - External MCP Servers (SSE, HTTP, stdio sub-processes)                         |
|  - Discovered Tool Schemas, Arguments, and Execution Outputs                      |
|  - Discovered Workspace Resources & Content Payloads                              |
|  - Discovered Prompt Templates & Rendered Role Messages                           |
+-----------------------------------------------------------------------------------+
```

### Core Security Invariants:
1. **Untrusted Labeling (`UNTRUSTED_MCP`)**: All external MCP tool returns, resource texts, and rendered prompt messages are labeled untrusted data and never become trusted system instructions.
2. **Backend Authority**: Frontend clients, LLM planners, and subagents cannot grant permissions, bypass confirmation tokens, override risk policies, or alter tenant identity.
3. **Tenant & Workspace Boundary**: Every server, tool, resource, prompt, and execution history record is strictly bound to `workspace_id` and verified against active workspace membership.

---

## 2. Threat Classification & Mitigation Matrix

| ID | Threat Name | Attack Vector | Severity | Mitigation & Verification |
|---|---|---|---|---|
| **T-01** | **Tenant Escape & IDOR** | Attacker queries User B's server/tool/resource ID in Workspace A | Critical | Direct `workspace_id` filtering in all queries; 404 response on unauthorized queries; tested in `test_mcp_tenant_isolation.py`. |
| **T-02** | **Confirmation Token Replay** | Attacker re-uses a consumed confirmation token to execute a restricted tool | High | Tokens are cryptographically bound (SHA-256) and immediately popped upon verification; tested in `test_mcp_confirmation_security.py`. |
| **T-03** | **Argument Tampering in Confirmation** | Attacker obtains confirmation for `rm file1` then passes `rm file2` with same token | High | Tokens bind `args_hash`; modification causes immediate token rejection. |
| **T-04** | **Prompt Injection via Tool Description** | MCP server embeds `Ignore all previous instructions...` in description | High | Regex and heuristic `PromptInjectionDetector` checks; Critic Agent validates provenance before generation. |
| **T-05** | **Tool Output Command Injection** | Malicious MCP tool returns `rm -rf /` or HTML tags in output | High | Output sanitized with `CredentialStore.redact_sensitive_dict`; frontend treats outputs as plain text without `dangerouslySetInnerHTML`. |
| **T-06** | **SSRF via Resource URI** | Resource URI targets `169.254.169.254`, `localhost`, or private subnets | Critical | `MCPValidator.validate_resource_uri` inspects hostnames and rejects private/loopback/AWS metadata IPs; tested in `test_mcp_protocol_security.py`. |
| **T-07** | **Local Filesystem Traversal** | Resource URI uses `file:///etc/passwd` or `..` paths | Critical | `file://` scheme and `..` paths explicitly prohibited by `MCPValidator`. |
| **T-08** | **Command Injection in STDIO Transport** | Server URL uses shell metacharacters (`;`, `&&`, `|`, `` ` ``) | Critical | `DANGEROUS_URL_CHARACTERS` regex validation and non-shell subprocess execution. |
| **T-09** | **Recursive / Malicious JSON Schema** | MCP server serves deeply nested schema to cause stack overflow / DoS | Medium | Schema depth bounded to $\le 6$; properties count bounded to $\le 50$; tested in `test_mcp_protocol_security.py`. |
| **T-10** | **Oversized Payloads & DoS** | Client submits huge arguments (>32KB) or server returns massive output | Medium | Tool arguments bounded to 32KB; prompt arguments bounded to 32KB; resource texts truncated at 1MB. |
| **T-11** | **Credential Leakage** | API keys or passwords logged in plain text or exposed in execution state | High | `CredentialStore.mask_credential` and `redact_sensitive_dict` redact all sensitive key patterns. |
| **T-12** | **Stale & Disabled Capability Execution** | Client calls capability that has changed or been disabled | Medium | Strict check `enabled == True` and `is_stale == False`; returns 400/404 on violation. |
| **T-13** | **Cache Tenant Leakage** | Tenant A's cached tool results or capabilities returned to Tenant B | High | Redis keys scoped by `aegis:mcp:{workspace_id}:...`; tested in `test_mcp_cache_isolation.py`. |
| **T-14** | **SSE Stream Leakage** | User A subscribes to User B's execution stream | High | Stream channel validation enforces workspace membership verification before establishing SSE connection. |
| **T-15** | **Planner Authorization Bypass** | Planner hallucinates `admin=True` or `requires_confirmation=False` | High | Planner outputs are untrusted; downstream `ToolExecutorAgent` and `MCPSecurityService` re-verify every parameter. |
| **T-16** | **Fabricated Citation / Provenance** | Agent fabricates citations for non-existent tools or cross-tenant tools | High | `CriticAgent` inspects execution trace and fails verification (`CriticDecision.FAIL`) on invalid provenance. |

---

## 3. Security Evaluation Precedence

The MCP Security Layer strictly enforces deterministic precedence:
1. **Authentication** (JWT bearer verification)
2. **Workspace Membership** (User belongs to active workspace)
3. **Tenant Isolation** (Entities match `workspace_id`)
4. **Server Status** (Server is active and enabled)
5. **Capability Status** (Capability is enabled and not stale)
6. **RBAC Permissions** (User possesses required `mcp:*` permission)
7. **Risk Policy & Safety Evaluation** (`SAFE`, `RESTRICTED`, `INVALID`)
8. **Confirmation Gate** (Single-use token required for restricted tools)
9. **Rate Limiting** (Sliding-window quota check)

No lower-level rule or user permission can override a higher-level denial.
