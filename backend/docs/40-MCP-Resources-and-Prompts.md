# AegisAI — Phase 6.5: MCP Resources & Prompts Subsystem

## 1. Executive Summary

Phase 6.5 introduces the secure, tenant-isolated MCP Resources and Prompts subsystems into AegisAI. External resource content and prompt templates are strictly classified and treated as **untrusted data**. The system prevents path traversal, local filesystem access, private network SSRF, prompt injection, and system prompt override attempts, while providing high-performance Redis caching, bounded size limits, multi-agent citation provenance, and an interactive frontend explorer.

---

## 2. Resource Subsystem Architecture

```
 External MCP Server
          │
          ▼
   ┌──────────────────────────────────────────────────────────┐
   │                  MCPResourceService                      │
   │  1. Tenant & Server Isolation Check (user_id/workspace_id)│
   │  2. Resource State Check (Active, Enabled, Non-Stale)    │
   │  3. URI Validation (Allowed schemes, No traversal/SSRF)  │
   │  4. Redis Cache Check (Key: aegis:mcp:resource:{...})    │
   │  5. MCP Transport Read ("resources/read")                │
   │  6. Bounded 1MB Size Limit (Sets truncated: true if over)│
   │  7. Sanitization (Strips scripts/HTML, redacts secrets)  │
   │  8. Redis Caching (300s TTL)                             │
   └───────────┬──────────────────────────────────────────────┘
               │
               ▼
   ┌───────────────────────┐
   │    Agent / RAG / UI   │ ◄─── Consumes as UNTRUSTED EXTERNAL DATA
   └───────────────────────┘
```

### 2.1 URI Security Rules & SSRF Defenses

| Threat | Check Mechanism | Result |
| :--- | :--- | :--- |
| **Path Traversal** | Detects `..`, leading `/` or `\` | `MCPValidationError` |
| **Local Filesystem** | Detects `file://` or `file:\` schemes | `MCPValidationError` |
| **Cloud Metadata** | Blocks `169.254.169.254` | `MCPValidationError` |
| **Loopback / Internal**| Blocks `localhost`, `127.0.0.1`, `0.0.0.0`, `10.0.0.0/8`, `192.168.0.0/16`, `172.16.0.0/12` | `MCPValidationError` |
| **Embedded Credentials**| Blocks `user:pass@host` | `MCPValidationError` |

---

## 3. Prompt Template Subsystem Architecture

```
 External MCP Server
          │
          ▼
   ┌──────────────────────────────────────────────────────────┐
   │                   MCPPromptService                       │
   │  1. Tenant & Server Isolation Check (user_id/workspace_id)│
   │  2. Prompt State Check (Active, Enabled, Non-Stale)      │
   │  3. Argument Validation (Required, Types, Max 32KB)      │
   │  4. MCP Transport Call ("prompts/get")                   │
   │  5. Security Boundary & Role Normalization               │
   │     • Role "system" messages marked strictly UNTRUSTED   │
   │     • Never overrides AegisAI internal system prompt     │
   │  6. Content Sanitization & Redaction                     │
   └───────────┬──────────────────────────────────────────────┘
               │
               ▼
   ┌───────────────────────┐
   │  Multi-Agent Context  │ ◄─── Passed strictly as untrusted user evidence
   └───────────────────────┘
```

---

## 4. Multi-Agent Engine & Security Integration

- **`CriticAgent`** ([`backend/app/core/agent/critic.py`](file:///d:/CP/AegisAI/backend/app/core/agent/critic.py)):
  - Validates citation provenance for `source_type="mcp_resource"` and `source_type="mcp_prompt"`.
  - Fails tasks with `CRITICAL` severity if fabricated or cross-tenant MCP citations are detected.
- **`ResponseGeneratorAgent`** ([`backend/app/core/agent/response.py`](file:///d:/CP/AegisAI/backend/app/core/agent/response.py)):
  - Distinguishes and cites `source_type="mcp_resource"` and `source_type="mcp_prompt"`.

---

## 5. REST APIs

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/mcp/resources` | Lists discovered MCP resources with pagination and search. |
| `POST` | `/api/v1/mcp/resources/search` | Performs ranked search over resources. |
| `GET` | `/api/v1/mcp/resources/{id}` | Retrieves resource metadata. |
| `POST` | `/api/v1/mcp/resources/{id}/read` | Reads sanitized content with size bounding. |
| `POST` | `/api/v1/mcp/resources/{id}/enable` | Enables a resource. |
| `POST` | `/api/v1/mcp/resources/{id}/disable` | Disables a resource. |
| `GET` | `/api/v1/mcp/prompts` | Lists discovered prompt templates. |
| `POST` | `/api/v1/mcp/prompts/search` | Performs ranked search over prompt templates. |
| `GET` | `/api/v1/mcp/prompts/{id}` | Retrieves prompt template argument schema. |
| `POST` | `/api/v1/mcp/prompts/{id}/render` | Renders a template with bound arguments. |
| `POST` | `/api/v1/mcp/prompts/{id}/enable` | Enables a prompt template. |
| `POST` | `/api/v1/mcp/prompts/{id}/disable` | Disables a prompt template. |

---

## 6. Verification Results

- **Backend Unit Tests**: **274 / 274 passing (100%)**
  ```bash
  pytest tests/unit/ -v
  ====================== 274 passed, 57 warnings in 49.69s ======================
  ```
- **Frontend Production Build**: **Clean Vite build in 2.17s**
  ```bash
  npm run build
  ✓ built in 2.17s
  ```
- **Git Branch**: `phase-6-mcp-platform`
