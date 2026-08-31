# Phase 7.2: Visual Workflow Builder + Node Editor

## Overview
Phase 7.2 delivers a production-grade visual workflow editor built on top of React Flow (`@xyflow/react`) and the Phase 7.1 Workflow Engine Foundation. It provides an interactive DAG canvas, drag-and-drop node creation, structured node and edge property inspectors, optimistic concurrency version protection, atomic bulk definition persistence, topological auto-layout, undo/redo history, and in-editor execution capabilities.

---

## 1. Visual Editor Architecture

```mermaid
graph TD
    Palette[Node Palette<br/>13 Node Types] -->|Drag / Click| Canvas[React Flow Canvas<br/>Topological DAG Graph]
    Canvas -->|Select Node| NodeInspector[Node Inspector<br/>Structured Configuration]
    Canvas -->|Select Edge| EdgeInspector[Edge Inspector<br/>Priority & Guards]
    Canvas -->|Save / Validate| BackendAPI[FastAPI Workflows API<br/>/workflows/{id}/definition]
    BackendAPI --> Validation[WorkflowValidationService<br/>Kahn's DAG Cycle Check]
    BackendAPI --> AtomicDB[(PostgreSQL / SQLite<br/>Atomic Transaction & Version Bump)]
```

### Components Created
- `UserWorkflowEditor.jsx`: Full-canvas workflow builder page wrapped with `ReactFlowProvider`, state undo/redo manager, validation banner, test execution runner, and auto-layout generator.
- `WorkflowNode.jsx`: Custom node component with AegisAI futuristic glassmorphism styling, type-specific badges, status indicators, and connection handles.
- `WorkflowNodePalette.jsx`: Searchable 13-node palette categorized into *Control Flow*, *AI & Cognition*, and *MCP & Integrations*. Prevents multiple START node additions.
- `WorkflowNodeEditor.jsx`: Safe structured inspector for node properties (goal, query, top_k, similarity, max depth, MCP tool catalog integration, mapping tables) without `eval()`.
- `WorkflowEdgeEditor.jsx`: Inspector for edge execution priorities and conditional guards.
- `WorkflowVariablesPanel.jsx`: Modal for managing typed workflow variables (`string`, `number`, `boolean`, `json`) with secret masking.
- `WorkflowToolbar.jsx`: Top navigation toolbar featuring title editing, version pill, status pill, dirty state indicators, auto-layout, undo/redo, validation, activate/pause, and save actions.
- `WorkflowValidationPanel.jsx`: Interactive validation drawer with error breakdown and click-to-focus on offending nodes.

---

## 2. Supported Node Types & Configuration

| Category | Node Type | Configuration Fields | Risk / Isolation Level |
|---|---|---|---|
| **Control Flow** | `START` | `description`, `input_schema` | Exactly 1 per workflow |
| **Control Flow** | `END` | `output_template` | At least 1 per workflow |
| **Control Flow** | `CONDITION` | `left`, `operator` (`equals`, `contains`, `greater_than`), `right` | Declarative / Deterministic |
| **Control Flow** | `HUMAN_APPROVAL` | `title`, `description`, `approval_message`, `timeout` | Pauses for human confirmation |
| **Control Flow** | `TRANSFORM` | `mapping` (`target_field` $\to$ expression) | Safe string/variable replacement |
| **AI & Cognition** | `AGENT` | `agent_type`, `goal` | AegisAI Multi-Agent boundary |
| **AI & Cognition** | `RAG` | `query`, `top_k`, `similarity_threshold` | Workspace document isolation |
| **AI & Cognition** | `GRAPH` | `query`, `max_depth` | Knowledge Graph boundary |
| **AI & Cognition** | `MEMORY` | `query`, `category` | Memory store boundary |
| **MCP & Integrations** | `MCP_TOOL` | `tool_name`, `server_name` | Gated by MCP Confirmation & RBAC |
| **MCP & Integrations** | `MCP_RESOURCE` | `uri` | Displayed with `UNTRUSTED_MCP` badge |
| **MCP & Integrations** | `MCP_PROMPT` | `prompt_name`, `arguments` | Displayed with `UNTRUSTED_MCP` badge |
| **MCP & Integrations** | `LOCAL_TOOL` | `tool_name` | Whitelisted system utilities |

---

## 3. Atomic Graph Persistence & Optimistic Concurrency

### Optimistic Versioning Check
When saving a visual workflow definition, the client submits `expected_version`. If the workflow version in the database has changed since loading:
1. Backend raises `VersionConflictError` $\to$ HTTP 409 Conflict.
2. Frontend displays: *"Workflow was modified by another session. Please reload the latest definition before saving."*
3. Stale overwrites are completely prevented.

### Atomic Transaction
All node replacements, edge replacements, variable synchronizations, and version bumps occur within a single database transaction. If any graph validation rule fails (e.g. cycle introduced), the entire transaction rolls back cleanly.

---

## 4. REST API Extensions

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/workflows/{id}/definition` | Retrieves complete graph definition for visual canvas |
| `PUT` | `/api/v1/workflows/{id}/definition` | Atomically saves graph definition with optimistic version check |
| `POST` | `/api/v1/workflows/{id}/clone` | Clones workflow into a new draft workflow with all nodes and edges |

---

## 5. Verification Metrics

- **Unit Test Regression**: **340 / 340 PASSED (100%)**
  - 334 previous baseline tests
  - 6 new Phase 7.2 tests across graph definition retrieval, definition update, optimistic version conflict, atomic rollback on cyclic graph, archived workflow edit prevention, and workflow cloning.
- **Frontend Production Build**: Vite production build completed in 761ms with **0 errors**.
- **Database Migration**: **No migration required** (Phase 7.1 schema 011 natively supports positions, configs, conditions, and priorities).
