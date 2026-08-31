# AegisAI — Phase 6.2: MCP Server Registry & Advanced Discovery

## 1. Overview

Phase 6.2 advances the AegisAI Model Context Protocol (MCP) subsystem from the initial foundation into a production-grade server registry and dynamic capability discovery engine. It introduces connection lifecycle management, bounded timeouts, transient fault retries, deterministic capability versioning via SHA-256 definition hashing, soft-stale capability tracking, automatic reactivation, active health monitoring, concurrency locks, prompt injection hardening, and interactive management UI capabilities.

---

## 2. Advanced Architecture

```
                                 ┌─────────────────────────────────┐
                                 │   Frontend MCP Management UI    │
                                 │  (Health, Discovery, Catalog)   │
                                 └────────────────┬────────────────┘
                                                  │ HTTP / REST
                                                  ▼
                                 ┌─────────────────────────────────┐
                                 │       FastAPI MCP Router        │
                                 │      (/api/v1/mcp/servers)      │
                                 └────────┬───────────────┬────────┘
                                          │               │
                         ┌────────────────┴───┐       ┌───┴────────────────┐
                         ▼                    ▼       ▼                    ▼
              ┌──────────────────────┐             ┌──────────────────────┐
              │  MCPRegistryService  │             │ MCPDiscoveryService  │
              │(CRUD, Health, Catalog│             │(Hashing, Versioning) │
              └──────────┬───────────┘             └──────────┬───────────┘
                         │                                    │
                         ▼                                    ▼
              ┌──────────────────────┐             ┌──────────────────────┐
              │ MCPConnectionManager │             │   Redis / Lock Mutex │
              │(Timeout, Retries,    │             │  (aegis:mcp:         │
              │ Ping, Handshake)     │             │   discovery:<id>)    │
              └──────────┬───────────┘             └──────────┬───────────┘
                         │                                    │
                         ▼                                    ▼
              ┌──────────────────────┐             ┌──────────────────────┐
              │ PostgreSQL Database  │             │ External MCP Server  │
              │ (Servers, Hashes,    │             │ (Tools, Resources,   │
              │  Stale State, Ver)   │             │  Prompts Handshake)  │
              └──────────────────────┘             └──────────────────────┘
```

---

## 3. Database Layer & Migration

### 3.1 Migration `010_mcp_advanced_discovery.py`
- Upgraded `mcp_servers` and `mcp_capabilities` tables with down-revision `009_mcp_platform`.
- Head status verified: `010_mcp_advanced_discovery (head)`.

### 3.2 Schema Additions
- **`MCPServer`** (`backend/app/models/mcp.py`):
  - `server_version`: String(50), captured during handshake.
  - `protocol_version`: String(50), negotiated protocol standard (default `2024-11-05`).
  - `last_health_check_at`: DateTime(timezone=True), timestamp of last ping probe.
  - `last_discovery_at`: DateTime(timezone=True), timestamp of last synchronization.
  - `last_error`: Text, sanitized error message without credentials or stack traces.
  - Index on `server_url`.

- **`MCPCapability`** (`backend/app/models/mcp.py`):
  - `definition_hash`: String(64), indexed SHA-256 hash of normalized capability definition.
  - `is_stale`: Boolean, indexed flag indicating whether capability disappeared on latest discovery.
  - `stale_at`: DateTime(timezone=True), timestamp when capability disappeared.
  - `first_discovered_at`: DateTime(timezone=True), initial synchronization timestamp.
  - `last_discovered_at`: DateTime(timezone=True), latest synchronization timestamp.
  - `version`: Integer, revision counter incremented upon specification changes.

---

## 4. Connection Lifecycle & Resilience

### 4.1 `MCPConnectionManager` (`backend/app/core/mcp/connection.py`)
- **Bounded Timeouts**: Default 10.0s, upper-bound capped at 30.0s. All async socket and HTTP operations are guarded with `asyncio.wait_for`.
- **Transient Retries**: Exponential backoff with jitter (`delay = base * (2^(attempt-1)) + jitter`) for network resets, socket drops, and 5xx responses.
- **Fail-Fast Error Handling**: Non-retryable exceptions (`MCPAuthError`, `MCPValidationError`, `ValueError`) fail immediately on attempt 1 without retry.
- **Health Ping**: Rapid latency measurement probe (`ping_health`) with millisecond precision.

---

## 5. Capability Normalization & Versioning

### 5.1 `MCPNormalizer` (`backend/app/core/mcp/normalization.py`)
- **Canonical Schema Sort**: Recursively sorts JSON Schema dictionaries and arrays for deterministic serialization.
- **SHA-256 Hashing**:
  ```python
  def_hash = MCPNormalizer.compute_definition_hash(
      capability_type=MCPCapabilityType.TOOL,
      name="calculator",
      description="Perform arithmetic operations",
      input_schema={...},
      meta_data={...}
  )
  ```
- **Prompt Injection Defense**: Sanitizes external descriptions and metadata, stripping control characters (`\x00-\x1F`) and ensuring untrusted input remains inert data.

### 5.2 Discovery Lifecycle (`backend/app/services/mcp/mcp_discovery.py`)
1. **Concurrency Lock**: Acquires Redis distributed lock (`aegis:mcp:discovery:{server_id}`) for 45s, rejecting duplicate simultaneous discovery triggers.
2. **Handshake**: Initializes session via `MCPConnectionManager`.
3. **Change Detection**:
   - **Unchanged**: Existing hash matches new hash $\rightarrow$ updates `last_discovered_at`.
   - **Modified**: Existing hash differs $\rightarrow$ updates definition, increments `version = version + 1`.
   - **Added**: New capability key $\rightarrow$ inserts record with `version = 1`.
   - **Soft-Stale**: Previously known capability missing in response $\rightarrow$ sets `is_stale = True`, `stale_at = now`.
   - **Reactivated**: Previously stale capability returned $\rightarrow$ clears `is_stale = False`, `stale_at = None`.

---

## 6. REST API Endpoints

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/mcp/servers` | Register server with duplicate URL/name checks | Yes |
| `GET` | `/api/v1/mcp/servers` | List workspace servers with capability count | Yes |
| `GET` | `/api/v1/mcp/servers/{server_id}` | Get server details and status | Yes |
| `PATCH` | `/api/v1/mcp/servers/{server_id}` | Update server configuration | Yes |
| `DELETE` | `/api/v1/mcp/servers/{server_id}` | Delete server and cascade capabilities | Yes |
| `POST` | `/api/v1/mcp/servers/{server_id}/discover` | Run capability discovery synchronization | Yes |
| `POST` | `/api/v1/mcp/servers/{server_id}/refresh` | Force refresh discovery with detailed change metrics | Yes |
| `GET` | `/api/v1/mcp/servers/{server_id}/health` | Run active ping health check | Yes |
| `GET` | `/api/v1/mcp/servers/{server_id}/capabilities` | List capabilities with search & stale filtering | Yes |
| `GET` | `/api/v1/mcp/servers/{server_id}/tools` | List server tools | Yes |
| `GET` | `/api/v1/mcp/servers/{server_id}/resources` | List server resources | Yes |
| `GET` | `/api/v1/mcp/servers/{server_id}/prompts` | List server prompts | Yes |
| `GET` | `/api/v1/mcp/capabilities/{capability_id}` | Get single capability JSON Schema and version | Yes |
| `POST` | `/api/v1/mcp/servers/{server_id}/enable` | Enable server | Yes |
| `POST` | `/api/v1/mcp/servers/{server_id}/disable` | Disable server | Yes |

---

## 7. Frontend Management Dashboard

- **TypeScript API Client** ([`frontend/src/api/mcp.ts`](file:///d:/CP/AegisAI/frontend/src/api/mcp.ts)):
  - Full typed support for `checkServerHealth`, `refreshServerDiscovery`, `listServerTools`, `listServerResources`, `listServerPrompts`, and `getCapabilityDetails`.
- **Interactive UI** ([`frontend/src/pages/user/UserMcpMarket.jsx`](file:///d:/CP/AegisAI/frontend/src/pages/user/UserMcpMarket.jsx)):
  - **Health Monitoring**: Dedicated health ping button with real-time latency readout (e.g. `14.2ms`) and status badges.
  - **Discovery Breakdown**: Modal displaying granular metrics (`tools_added`, `tools_changed`, `resources_added`, `prompts_added`, `stale_capabilities`, `reactivated_capabilities`).
  - **Catalog Inspector**: Tabbed navigation between Tools, Resources, and Prompts with real-time search filtering, JSON Schema viewer, version badges (`v1`, `v2`), and `STALE` indicators.

---

## 8. Verification & Quality Assurance

- **Backend Unit Tests**: **246 / 246 tests passing (100%)**
  - Added 7 new Phase 6.2 tests covering timeouts, retries, ping probes, stale lifecycle, reactivation, definition hashing, and endpoint metrics.
- **Frontend Production Build**: Clean Vite production build (`npm run build`) in 2.82s.
- **Database Migration**: Alembic upgrade to `010_mcp_advanced_discovery (head)` verified.
- **Git Branch**: `phase-6-mcp-platform`
