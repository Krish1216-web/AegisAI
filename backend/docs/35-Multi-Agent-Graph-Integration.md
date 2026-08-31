# AegisAI — Phase 5.9: Multi-Agent Knowledge Graph Integration

## 1. Overview

Phase 5.9 completes the integration of Knowledge Graph reasoning into the core LangGraph multi-agent cognitive architecture of AegisAI. With this capability, autonomous agents can:
1. Intelligently recognize when domain topology, pathfinding, dependency chains, or entity relationship questions require graph reasoning.
2. Formulate dynamic graph execution plans via `OrchestratorAgent` (`TaskType.GRAPH_QUERY` and `TaskType.HYBRID_GRAPH_RAG`).
3. Traverse tenant-isolated subgraphs, compute multi-hop shortest paths, and generate grounded graph contexts via `GraphReasoningAgent`.
4. Validate graph citations and reject hallucinated edges/nodes via `CriticAgent`.
5. Synthesize multi-source grounded answers combining Vector RAG evidence, long-term Semantic Memory, and Knowledge Graph topology via `ResponseGeneratorAgent`.

---

## 2. Multi-Agent Pipeline Architecture

```
                                 ┌───────────────────────┐
                                 │   User Query / SSE    │
                                 └──────────┬────────────┘
                                            │
                                            ▼
                                 ┌───────────────────────┐
                                 │   OrchestratorAgent   │
                                 └──────────┬────────────┘
                                            │
                                            ▼
                                 ┌───────────────────────┐
                                 │     PlannerAgent      │
                                 └──────────┬────────────┘
                                            │
               ┌────────────────────────────┼────────────────────────────┐
               │                            │                            │
               ▼                            ▼                            ▼
      ┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
      │   MemoryAgent   │          │GraphReasoningAg │          │    RAGAgent     │
      │ (Semantic Mem)  │          │ (KG Topology)   │          │ (Vector Chunks) │
      └────────┬────────┘          └────────┬────────┘          └────────┬────────┘
               │                            │                            │
               └────────────────────────────┼────────────────────────────┘
                                            │
                                            ▼
                                 ┌───────────────────────┐
                                 │   Research / Tools    │
                                 └──────────┬────────────┘
                                            │
                                            ▼
                                 ┌───────────────────────┐
                                 │      CriticAgent      │
                                 │ (Citation Validation) │
                                 └──────────┬────────────┘
                                            │
                                            ▼
                                 ┌───────────────────────┐
                                 │ ResponseGeneratorAg   │
                                 │ (Attributed Synthesis)│
                                 └───────────────────────┘
```

---

## 3. Core Components

### 3.1 GraphReasoningAgent (`backend/app/core/agent/graph_reasoning.py`)
- **Intent Analysis**: Uses `QueryEntityExtractor` to identify domain entities and concepts in the prompt.
- **Topological Matching**: Matches extracted query concepts against workspace entity nodes and alias dictionaries.
- **Shortest-Path Discovery**: When multiple entities are mentioned, computes multi-hop shortest paths up to depth 4 using `KnowledgeGraphIntelligenceService`.
- **Graph Citations**: Generates authentic citation objects (`source_type="graph"` and `source_type="graph_edge"`) linking to valid database node and edge IDs.
- **Tenant Isolation**: Strictly confines entity discovery, edge traversal, and shortest-path computation to `user_id` and `workspace_id`.

### 3.2 Orchestrator Agent Classification (`backend/app/core/agent/orchestrator.py`)
- Extends task classification with `TaskType.GRAPH_QUERY` and `TaskType.HYBRID_GRAPH_RAG`.
- Dynamically provisions `AgentType.GRAPH` into `required_agents` based on relationship keywords, dependency queries, and entity names.

### 3.3 Critic Citation Verification (`backend/app/core/agent/critic.py`)
- Intercepts all graph citations (`source_type in ("graph", "graph_edge")`).
- Validates node IDs against UUID formatting and tenant graph constraints.
- Emits `CriticDecision.FAIL` or `CriticDecision.RETRY` when fabricated nodes/edges are detected.

### 3.4 Response Generator Synthesis (`backend/app/core/agent/response.py`)
- Incorporates `graph_context` into the LLM prompt.
- Outputs structured responses with unified citations across Knowledge Graph, RAG documents, and Research.

---

## 4. API Endpoints

### `POST /api/v1/knowledge-graph/reason`
Executes multi-agent graph reasoning directly on tenant data.

#### Request Body
```json
{
  "query": "How is AegisAI Core related to PostgreSQL Engine?",
  "depth": 2,
  "include_rag": true,
  "include_memory": true
}
```

#### Response Body
```json
{
  "query": "How is AegisAI Core related to PostgreSQL Engine?",
  "entities": ["AegisAI Core", "PostgreSQL Engine"],
  "matched_nodes_count": 2,
  "matched_edges_count": 1,
  "paths_found": 1,
  "graph_context": "=== KNOWLEDGE GRAPH TOPOLOGY ===\n- Project (AegisAI Core) USES Skill (PostgreSQL Engine)",
  "citations": [
    {
      "source_type": "graph",
      "node_id": "8c68a5dc-657d-4200-807f-4baa015b97bf",
      "node_name": "AegisAI Core",
      "node_type": "PROJECT",
      "confidence": 0.95
    },
    {
      "source_type": "graph_edge",
      "edge_id": "3b36d2aa-ff7b-4c62-9e23-74b86861214c",
      "source_node_id": "8c68a5dc-657d-4200-807f-4baa015b97bf",
      "target_node_id": "670498a4-0e31-4158-b673-c6ec44ef8796",
      "relationship_type": "USES",
      "confidence": 0.98
    }
  ],
  "confidence": 0.90,
  "latency_ms": 14.5
}
```

---

## 5. Frontend Interactive "Ask Graph" UI

Integrated into `frontend/src/pages/user/UserGraph.jsx`:
- **"Ask Graph" Toolbar Button**: Launches the interactive reasoning modal.
- **Natural Language Question Input**: Allows users to type free-form graph and relationship queries.
- **Live Metric Badges**: Displays matched entities, connected edges, and reasoning confidence.
- **Grounded Graph Topology**: Displays structured topology and paths.
- **Click-to-Focus Graph Citations**: Clicking any cited entity auto-pans and centers the canvas camera directly onto the cited node.

---

## 6. Verification & Test Baseline

- **Unit Tests**: 219/219 passing (`pytest tests/unit/`).
  - Added `tests/unit/test_graph_reasoning_agent.py` covering reasoning execution, orchestrator classification, critic citation validation, response generator citations, and full pipeline execution.
- **Frontend Production Build**: Vite build succeeds cleanly with zero bundle errors (`npm run build`).
- **Tenant Isolation**: Verified across all graph traversal, memory sync, and multi-agent reasoning paths.
