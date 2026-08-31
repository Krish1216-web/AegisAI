# AegisAI — Phase 6.4: MCP Tool Execution Subsystem

## 1. Executive Summary

Phase 6.4 introduces the secure, tenant-isolated MCP Tool Execution Engine into AegisAI. This subsystem allows authorized users and the multi-agent cognitive architecture to safely invoke external MCP tools with rigorous JSON Schema argument validation, deterministic risk policies (`SAFE`, `RESTRICTED`, `INVALID`), single-use human confirmation gating for restricted capabilities, concurrency locking, transient error retries, bounded timeouts, output sanitization, and prompt injection defense.

---

## 2. Target Execution Architecture

```
 User Request / Multi-Agent Step
               │
               ▼
   ┌───────────────────────┐
   │    Planner / Agent    │
   │ (Identifies MCP Tool) │
   └───────────┬───────────┘
               │
               ▼
   ┌──────────────────────────────────────────────────────────┐
   │                MCPToolExecutionService                   │
   │  1. Tenant & Tool Validation (Active Server & Capability)│
   │  2. JSON Schema Argument Validation (Type, Bounds, Props)│
   │  3. Rule-Based Safety Assessment (ToolRiskPolicy)        │
   │  4. Confirmation Gate (Single-use token for RESTRICTED)  │
   │  5. Redis Concurrency Lock (aegis:mcp:exec:{id}:{user}) │
   │  6. Bounded Connection & Handshake                       │
   │  7. JSON-RPC 2.0 "tools/call" Execution                  │
   │  8. Transient Retry with Exponential Jitter Backoff      │
   │  9. Sensitive Credential Redaction & Sanitization        │
   │ 10. Database Execution Persistence (ToolExecution)       │
   └───────────┬──────────────────────────────────────────────┘
               │
               ▼
   ┌───────────────────────┐
   │      CriticAgent      │ ◄─── Validates provenance and integrity
   └───────────┬───────────┘
               │
               ▼
   ┌───────────────────────┐
   │ResponseGeneratorAgent │ ◄─── Attributes source_type="mcp_tool"
   └───────────────────────┘
```

---

## 3. Human Confirmation & Risk Policy Gating

### 3.1 Policy Decisions

| Risk Level | Policy Decision | Execution Requirement |
| :--- | :--- | :--- |
| **`SAFE`** | `ALLOW` | Executed directly if server and tool are active, enabled, and non-stale. |
| **`RESTRICTED`** | `REQUIRE_CONFIRMATION` | Returns HTTP `428 Precondition Required`. Requires obtaining a cryptographic single-use confirmation token bound to `(user_id, workspace_id, tool_id, argument_hash)`. Token expires in 300s and cannot be replayed. |
| **`INVALID`** | `DENY` | Rejects execution immediately with HTTP `400 Bad Request`. Client overrides are strictly prohibited. |

### 3.2 Confirmation Token Binding
Confirmation tokens are cryptographically generated and stored with SHA-256 argument fingerprinting:
```python
args_hash = hashlib.sha256(json.dumps(arguments, sort_keys=True).encode()).hexdigest()
raw_token = f"{user_id}:{workspace_id}:{tool_id}:{args_hash}:{uuid.uuid4()}"
token = hashlib.sha256(raw_token.encode()).hexdigest()
```
Upon execution, the token is consumed once and popped from the active registry to prevent replay attacks.

---

## 4. Multi-Agent Engine Integration

- **`ToolExecutorAgent`** ([`backend/app/core/agent/executor.py`](file:///d:/CP/AegisAI/backend/app/core/agent/executor.py)):
  - Dynamically distinguishes between local built-in tools (`calculator`, `weather`, `search`) and external MCP capabilities (`mcp:tool_name` or `tool_source="MCP"`).
  - Automatically delegates MCP execution to `MCPToolExecutionService`.
- **`CriticAgent`** ([`backend/app/core/agent/critic.py`](file:///d:/CP/AegisAI/backend/app/core/agent/critic.py)):
  - Validates execution result integrity, rejects fabricated tool claims, and ensures cross-tenant isolation.
- **`ResponseGeneratorAgent`** ([`backend/app/core/agent/response.py`](file:///d:/CP/AegisAI/backend/app/core/agent/response.py)):
  - Formulates user responses citing `source_type="mcp_tool"`.

---

## 5. REST APIs

| Method | Endpoint | Description | Status Codes |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/mcp/tools/{id}/confirm` | Generates a single-use confirmation token for a RESTRICTED tool execution. | `200 OK`, `404 Not Found` |
| `POST` | `/api/v1/mcp/tools/{id}/execute` | Safely executes an MCP tool with JSON Schema validation and sanitized output. | `200 OK`, `400 Bad Request`, `428 Precondition Required`, `502 Bad Gateway` |

---

## 6. Frontend Execution UI

- **Interactive Schema-Driven Form**:
  - Dynamically generates input controls for strings, numbers, integers, and booleans with descriptions and required badges.
- **Restricted Tool Warning Banner**:
  - Highlights dangerous operations and automatically manages single-use token confirmation before invocation.
- **Execution Output Inspector**:
  - Displays formatted JSON output with latency badge in milliseconds and one-click copy button.

---

## 7. Verification Results

- **Backend Unit Tests**: **264 / 264 passing (100%)**
  ```bash
  pytest tests/unit/ -v
  ====================== 264 passed, 56 warnings in 53.70s ======================
  ```
- **Frontend Production Build**: **Clean Vite build in 2.15s**
  ```bash
  npm run build
  ✓ built in 2.15s
  ```
- **Git Branch**: `phase-6-mcp-platform`
