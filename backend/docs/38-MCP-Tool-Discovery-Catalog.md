# AegisAI — Phase 6.3: MCP Tool Discovery & Catalog

## 1. Overview

Phase 6.3 establishes a dedicated, first-class MCP Tool Catalog within AegisAI. Building upon the Phase 6.1 and 6.2 foundation, this layer provides deterministic ranked search, explainable rule-based risk classification (`SAFE`, `RESTRICTED`, `INVALID`), parameter inspection, enable/disable controls, execution readiness flags (`available_for_execution`), prompt injection defense, and frontend catalog explorer tooling—preparing the system for dynamic tool execution in Phase 6.4 without executing tools in Phase 6.3.

---

## 2. Tool Catalog Architecture

```
                               ┌────────────────────────────────┐
                               │   Frontend MCP Tool Catalog    │
                               │   (Search, Filter, Inspector)  │
                               └───────────────┬────────────────┘
                                               │ HTTP / REST
                                               ▼
                               ┌────────────────────────────────┐
                               │       FastAPI MCP Router       │
                               │      (/api/v1/mcp/tools)       │
                               └───────────────┬────────────────┘
                                               │
                               ┌───────────────┴────────────────┐
                               ▼                                ▼
                    ┌──────────────────────┐         ┌──────────────────────┐
                    │ MCPToolCatalogService│         │    ToolRiskPolicy    │
                    │(Ranked Search, Filter│         │(Rule-Based Risk Eval,│
                    │ Availability Check)  │         │ Prompt Injection Guard)
                    └──────────┬───────────┘         └──────────┬───────────┘
                               │                                │
                               ▼                                ▼
                    ┌───────────────────────────────────────────────────┐
                    │ PostgreSQL Database (mcp_servers, mcp_capabilities)│
                    └───────────────────────────────────────────────────┘
```

---

## 3. Tool Risk Policy & Prompt Injection Hardening

### 3.1 `ToolRiskPolicy` (`backend/app/core/mcp/policy.py`)
Deterministic classification evaluating tool names, descriptions, input schema properties, and metadata tags against high-risk pattern rules:

| Risk Level | Policy Decision | Criteria / Trigger Examples |
| :--- | :--- | :--- |
| **`SAFE`** | `ALLOW` | Standard read-only, computational, or API lookups without privileged shell or destructive operations. |
| **`RESTRICTED`** | `REQUIRE_CONFIRMATION` | Tools containing shell/command keywords (`shell`, `exec`, `subprocess`, `powershell`, `cmd`), destructive patterns (`rm -rf`, `drop database`, `truncate`), or credential extraction tags (`dump_env`, `read_secrets`). |
| **`INVALID`** | `DENY` | Empty names, malformed JSON schemas, or property counts exceeding bounded limits (> 50 properties). |

### 3.2 Prompt Injection Defense (`PromptInjectionDetector`)
- Untrusted tool descriptions, parameters, and metadata containing adversarial payload prompts (e.g. *"Ignore previous instructions"*, *"Reveal system prompt"*, *"Send API key"*) are treated strictly as inert data and never converted into AI system instructions.

---

## 4. Deterministic Ranked Search & Catalog Services

### 4.1 `MCPToolCatalogService` (`backend/app/services/mcp/mcp_tool_catalog.py`)
- **Ranking Hierarchy**:
  1. **Exact Name Match** (Score: 100)
  2. **Prefix Name Match** (Score: 80)
  3. **Substring Name Match** (Score: 60)
  4. **Description Keyword Match** (Score: 40)
  5. **Fuzzy Token Match** (Score: 20)
- **Execution Readiness Evaluation**:
  ```python
  available_for_execution = (
      server.enabled is True and
      server.status == MCPServerStatus.ACTIVE and
      capability.enabled is True and
      capability.is_stale is False and
      risk_level != "invalid"
  )
  ```

---

## 5. REST API Endpoints

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/mcp/tools` | List workspace tools with risk, server, transport, enabled, and stale filtering | Yes |
| `POST` | `/api/v1/mcp/tools/search` | Structured deterministic ranked search | Yes |
| `GET` | `/api/v1/mcp/tools/{tool_id}` | Detailed tool metadata, JSON Schema, risk assessment, and availability | Yes |
| `POST` | `/api/v1/mcp/tools/{tool_id}/enable` | Enable a specific tool capability | Yes |
| `POST` | `/api/v1/mcp/tools/{tool_id}/disable` | Disable a specific tool capability | Yes |

---

## 6. Frontend Tool Catalog UI

- **TypeScript API Client** ([`frontend/src/api/mcp.ts`](file:///d:/CP/AegisAI/frontend/src/api/mcp.ts)):
  - Added typed interfaces (`MCPTool`, `MCPToolSearchRequest`, `MCPToolSearchResponse`) and helpers (`listWorkspaceTools`, `searchWorkspaceTools`, `getToolDetails`, `enableMCPTool`, `disableMCPTool`).
- **Interactive UI** ([`frontend/src/pages/user/UserMcpMarket.jsx`](file:///d:/CP/AegisAI/frontend/src/pages/user/UserMcpMarket.jsx)):
  - **Tabbed Switcher**: Toggle between "Registered Servers" and "Tool Catalog".
  - **Debounced Search & Risk Filter Bar**: Filter by `All Risks`, `Safe`, `Restricted`, and `Invalid`.
  - **Tool Cards**: Displaying server name, transport, version, risk badge (`SAFE` emerald, `RESTRICTED` amber, `INVALID` rose), and execution readiness status.
  - **Tool Inspector Modal**: Parameter table displaying argument types, required flags, descriptions, risk explanation reasons, and raw JSON Schema viewer with plain-text rendering to prevent XSS.

---

## 7. Verification & Quality Assurance

- **Backend Unit Tests**: **258 / 258 tests passing (100%)**
  - Added 12 new dedicated Phase 6.3 unit tests across catalog listing, ranked search, schema validation bounds, risk assessment, prompt injection neutralization, and multi-tenant isolation.
- **Frontend Production Build**: Clean Vite production build (`npm run build`) in 2.02s.
- **Database Migration**: Verified on existing head `010_mcp_advanced_discovery`.
- **Git Branch**: `phase-6-mcp-platform`
