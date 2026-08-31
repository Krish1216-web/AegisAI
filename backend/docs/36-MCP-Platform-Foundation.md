# AegisAI — Phase 6.1: Model Context Protocol (MCP) Platform Foundation

## 1. Overview

Phase 6.1 establishes the foundational Model Context Protocol (MCP) subsystem within AegisAI. This platform layer enables tenant-isolated external tool server registration, safe protocol-compliant capability discovery (Tools, Resources, Prompts), strict schema validation, secure credential abstraction, REST APIs, and seamless integration preparation for the LangGraph multi-agent cognitive architecture.

---

## 2. MCP Subsystem Architecture

```
                               ┌─────────────────────────────┐
                               │  Frontend MCP Registry UI   │
                               └──────────────┬──────────────┘
                                              │ HTTP / JSON
                                              ▼
                               ┌─────────────────────────────┐
                               │     FastAPI MCP Router      │
                               │   (/api/v1/mcp/servers)     │
                               └──────┬───────────────┬──────┘
                                      │               │
                     ┌────────────────┴────┐     ┌────┴────────────────┐
                     ▼                     ▼     ▼                     ▼
          ┌─────────────────────┐             ┌─────────────────────┐
          │ MCPRegistryService  │             │ MCPDiscoveryService │
          └──────────┬──────────┘             └──────────┬──────────┘
                     │                                   │
                     ▼                                   ▼
          ┌─────────────────────┐             ┌─────────────────────┐
          │  MCPValidator &     │             │  MCPClientFactory   │
          │  CredentialStore    │             │ (SSE, HTTP, STDIO)  │
          └──────────┬──────────┘             └──────────┬──────────┘
                     │                                   │
                     ▼                                   ▼
          ┌─────────────────────┐             ┌─────────────────────┐
          │ PostgreSQL Database │             │ External MCP Server │
          │(mcp_servers,        │             │ (Tools, Resources,  │
          │ mcp_capabilities)   │             │  Prompts Handshake) │
          └─────────────────────┘             └─────────────────────┘
```

---

## 3. Database Layer & Migration

### 3.1 Migration `009_mcp_platform.py`
- Upgraded preliminary Phase 1 schema to production MCP models with down-revision `008_knowledge_graph`.
- Applied via Alembic: `009_mcp_platform (head)`.

### 3.2 Models (`backend/app/models/mcp.py`)
- **`MCPServer`**:
  - `id`: UUID Primary Key
  - `user_id`: UUID Foreign Key (`users.id`, `ondelete="CASCADE"`, indexed)
  - `workspace_id`: UUID Foreign Key (`workspaces.id`, `ondelete="CASCADE"`, indexed)
  - `name`: String(100), indexed
  - `description`: Text, optional
  - `server_url`: String(512)
  - `transport`: `MCPTransport` (`sse`, `streamable_http`, `stdio`)
  - `status`: `MCPServerStatus` (`active`, `inactive`, `error`, `disabled`)
  - `enabled`: Boolean, default True
  - `authentication_type`: `MCPAuthenticationType` (`none`, `api_key`, `bearer`, `oauth`)
  - `auth_config`: JSON (stores encrypted/masked credential references)
  - `metadata`: JSON (custom tags and properties)
  - `last_connected_at`: DateTime(timezone=True), optional
  - Unique Constraint: `(workspace_id, name)` ensuring server names are unique within each workspace.

- **`MCPCapability`**:
  - `id`: UUID Primary Key
  - `server_id`: UUID Foreign Key (`mcp_servers.id`, `ondelete="CASCADE"`, indexed)
  - `capability_type`: `MCPCapabilityType` (`tool`, `resource`, `prompt`, indexed)
  - `name`: String(100), indexed
  - `description`: Text, optional
  - `input_schema`: JSON (standard JSON Schema dictionary)
  - `metadata`: JSON
  - `enabled`: Boolean, default True
  - Unique Constraint: `(server_id, capability_type, name)`

---

## 4. Core MCP Protocol & Security

### 4.1 Base Client & Factory (`backend/app/core/mcp/`)
- **`BaseMCPClient`**: Abstract interface defining async protocol contracts (`initialize`, `list_tools`, `list_resources`, `list_prompts`, `ping`, `close`).
- **`MCPClientFactory`**: Dynamically instantiates the appropriate transport client (`MockMCPClient`, `SSEMCPClient`, `StreamableHTTPClient`, `STDIOMCPClient`).
- **`MockMCPClient`**: In-memory protocol simulator supporting deterministic tool schemas, resources, and prompt templates for local testing and CI/CD pipelines.

### 4.2 Security & Credential Protection (`security.py`, `validation.py`)
- **Credential Masking**: `CredentialStore.mask_credential` transforms secrets (e.g. `sk-1234567890abcdef` -> `sk-••••def`).
- **Secret Redaction**: `CredentialStore.redact_sensitive_dict` recursively strips tokens/passwords from audit logs and responses.
- **URL & Shell Injection Defense**: Prohibits command injection tokens (`;`, `|`, `&`, `$(...)`, `>`) and restricts transport protocols.
- **Schema Safety**: `MCPValidator.validate_tool_input_schema` validates JSON Schema trees and enforces maximum nesting depth `<= 6` and size `<= 32KB` to protect against parser DoS.

---

## 5. Services Layer

### 5.1 `MCPRegistryService` (`backend/app/services/mcp/mcp_registry.py`)
- `register_server`: Enforces workspace uniqueness, URL validation, and tenant scoping.
- `list_servers`: Paginated list of registered servers for current workspace with status filtering.
- `get_server` / `update_server` / `delete_server`: Complete tenant-isolated lifecycle management.
- `toggle_server`: Enables or disables server, auto-transitioning disabled servers to `MCPServerStatus.DISABLED`.
- `list_capabilities`: Returns discovered capabilities by type with pagination.

### 5.2 `MCPDiscoveryService` (`backend/app/services/mcp/mcp_discovery.py`)
- Executes safe, read-only protocol handshakes (`initialize()` -> `list_tools()` -> `list_resources()` -> `list_prompts()`).
- Normalizes and validates discovered tool schemas.
- Synchronizes with `mcp_capabilities` database records, updating modified tools and pruning stale ones.
- Records connection latency and updates `last_connected_at`.

---

## 6. REST API Endpoints

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/mcp/servers` | Register a new MCP server | Yes |
| `GET` | `/api/v1/mcp/servers` | List workspace MCP servers | Yes |
| `GET` | `/api/v1/mcp/servers/{server_id}` | Get server details with capability counts | Yes |
| `PATCH` | `/api/v1/mcp/servers/{server_id}` | Update server configuration | Yes |
| `DELETE` | `/api/v1/mcp/servers/{server_id}` | Delete server and cascade capabilities | Yes |
| `POST` | `/api/v1/mcp/servers/{server_id}/discover` | Trigger capability discovery | Yes |
| `GET` | `/api/v1/mcp/servers/{server_id}/capabilities` | List server tools, resources, and prompts | Yes |
| `POST` | `/api/v1/mcp/servers/{server_id}/enable` | Enable an MCP server | Yes |
| `POST` | `/api/v1/mcp/servers/{server_id}/disable` | Disable an MCP server | Yes |

---

## 7. Multi-Agent Cognitive Engine Preparation

- **`AgentState`** ([`backend/app/core/agent/state.py`](file:///d:/CP/AegisAI/backend/app/core/agent/state.py)):
  - Added non-breaking optional fields: `mcp_servers`, `mcp_capabilities`, `mcp_tools_available`.
- **`ToolExecutorAgent`** ([`backend/app/core/agent/executor.py`](file:///d:/CP/AegisAI/backend/app/core/agent/executor.py)):
  - Preserved existing tool execution compatibility while establishing extension points for future Phase 6.2 tool invocations.

---

## 8. Frontend Registry UI

- **API Client** ([`frontend/src/api/mcp.ts`](file:///d:/CP/AegisAI/frontend/src/api/mcp.ts)):
  - Strongly typed TypeScript client for all MCP endpoints.
- **Interactive UI** ([`frontend/src/pages/user/UserMcpMarket.jsx`](file:///d:/CP/AegisAI/frontend/src/pages/user/UserMcpMarket.jsx)):
  - Live server cards with status badges, transport tags, and capability counts.
  - Server registration modal with transport & auth selectors.
  - Live "Discover" capability trigger with spinning indicator.
  - Capabilities inspection modal featuring tabbed views for Tools, Resources, and Prompts, alongside JSON Schema viewer.
  - One-click server enable/disable toggle and deletion.

---

## 9. Verification & Quality Assurance

- **Backend Unit Test Suite**: **239 / 239 tests passing (100%)**
  - Added 20 dedicated MCP tests across registry, validation, discovery, security, and REST APIs.
- **Frontend Production Build**: Clean Vite production build with zero errors (`npm run build`).
- **Database Migration**: Alembic upgrade to `009_mcp_platform (head)` verified.
