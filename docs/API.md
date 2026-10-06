# AegisAI — REST & SSE API Reference Specification

## 1. Authentication & Headers

All requests to `/api/v1/*` (except public health and authentication endpoints) require a valid JWT Bearer token:

```http
Authorization: Bearer <JWT_ACCESS_TOKEN>
Content-Type: application/json
```

---

## 2. Platform Multi-Agent Intelligence Endpoints

### 2.1 Execute Multi-Agent Request
```http
POST /api/v1/platform/execute
```
**Request Body**:
```json
{
  "query": "Synthesize the security architecture and check compliance against SOC2.",
  "workspace_id": "ws_enterprise_alpha",
  "enable_rag": true,
  "enable_graph": true,
  "enable_mcp": true,
  "model_preference": "gpt-4o",
  "temperature": 0.2
}
```
**Response (Streaming SSE or JSON)**:
```json
{
  "execution_id": "exec_98124b89",
  "status": "COMPLETED",
  "final_answer": "### Security Architecture Summary\n\nAegisAI enforces dual-tier RBAC...",
  "citations": [
    {
      "source_document": "SECURITY-ARCHITECTURE.md",
      "page": 1,
      "quote": "AegisAI is engineered around the principle of Defense in Depth..."
    }
  ],
  "provenance": {
    "duration_seconds": 1.34,
    "agents_invoked": ["Planner", "Enterprise RAG", "Critic", "Synthesizer"],
    "critic_score": 0.98
  }
}
```

---

## 3. Memory Vault Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/memory/search` | Search semantic long-term vector memory (`?query=...&top_k=5`). |
| `POST` | `/api/v1/memory` | Create a new structured long-term memory unit. |
| `DELETE` | `/api/v1/memory/{memory_id}` | Permanently delete a memory unit. |
| `GET` | `/api/v1/memory/session/{session_id}` | Retrieve working memory session history. |
| `DELETE` | `/api/v1/memory/session/{session_id}` | Clear ephemeral working memory buffer. |

---

## 4. Enterprise Document & RAG Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/documents/upload` | Multipart file upload (PDF, DOCX, TXT, MD) and auto-indexing. |
| `GET` | `/api/v1/documents` | List uploaded workspace documents with parsing status. |
| `GET` | `/api/v1/documents/{doc_id}/chunks` | Retrieve semantic chunks and vector embedding offsets. |
| `POST` | `/api/v1/documents/search` | Execute hybrid vector/keyword RAG search across documents. |
| `DELETE` | `/api/v1/documents/{doc_id}` | Delete document and remove associated vector embeddings. |

---

## 5. Knowledge Graph Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/graph/triples` | List relational knowledge triples for workspace. |
| `POST` | `/api/v1/graph/triples` | Ingest new knowledge triple (`subject`, `predicate`, `object`). |
| `POST` | `/api/v1/graph/pathfinder` | Find BFS shortest path between two entities. |
| `GET` | `/api/v1/graph/subgraph/{entity}` | Extract radial $k$-hop neighborhood subgraph JSON. |
| `GET` | `/api/v1/graph/analytics` | Retrieve graph density, centrality, and health metrics. |

---

## 6. Model Context Protocol (MCP) Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/mcp/servers` | List registered MCP servers and connection status. |
| `POST` | `/api/v1/mcp/servers` | Register new MCP server (SSE, HTTP, STDIO, WS). |
| `GET` | `/api/v1/mcp/tools` | List discovered tool catalog and input schemas. |
| `POST` | `/api/v1/mcp/tools/{tool_name}/execute` | Invoke MCP tool with JSON arguments and sandboxing. |

---

## 7. Visual AI Workflow Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/workflows` | List workspace workflow DAG definitions. |
| `POST` | `/api/v1/workflows` | Create new workflow definition. |
| `PUT` | `/api/v1/workflows/{workflow_id}` | Atomically update workflow topology. |
| `POST` | `/api/v1/workflows/{workflow_id}/run` | Trigger asynchronous workflow execution. |
| `GET` | `/api/v1/workflows/runs/{run_id}` | Poll execution status and node logs. |
| `POST` | `/api/v1/workflows/approvals/{id}/decision` | Submit Human-in-the-loop approval decision. |

---

## 8. Admin & Governance Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/admin/users` | List workspace users and system role assignments. |
| `GET` | `/api/v1/admin/audit/logs` | Fetch cryptographic audit trail. |
| `GET` | `/api/v1/admin/audit/verify` | Verify SHA-256 ledger integrity. |
| `GET` | `/api/v1/admin/export` | Export compliance and audit logs (JSON/CSV). |
