# AegisAI Knowledge Graph Foundation

## 1. Overview

The AegisAI Knowledge Graph Foundation provides structured relational mapping between all domain entities inside the platform:
- **Core Entities**: Users, Workspaces, Projects, Tasks, Agents, Skills, Conversations, Memories, Documents, and Document Chunks.
- **Typed Relationships**: Directed edges with confidence scores and contextual metadata.
- **Tenant Boundaries**: Strict isolation preventing cross-user and cross-workspace traversal or linkage.
- **Graph Traversal Engine**: Safe Breadth-First Search (BFS) with depth constraints and cycle detection.
- **RAG & Agent Integration**: Extraction of subgraphs formatted as structured context for LLM prompt augmentation.

---

## 2. Database Schema

### 2.1 `knowledge_graph_nodes`
Represents an entity node within a workspace:

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | No | Primary Key |
| `user_id` | UUID | No | Foreign Key (`users.id` ON DELETE CASCADE) |
| `workspace_id` | UUID | No | Foreign Key (`workspaces.id` ON DELETE CASCADE) |
| `node_type` | VARCHAR(50) | No | Entity type enum string |
| `external_id` | VARCHAR(255) | Yes | External entity ID (e.g. Document UUID, Memory UUID) |
| `name` | VARCHAR(255) | No | Human-readable entity title |
| `description` | TEXT | Yes | Detailed description or summary |
| `metadata` | JSON | Yes | Arbitrary structured attributes (capped at 64 KB) |
| `created_at` | TIMESTAMPTZ | No | Timestamp of creation |
| `updated_at` | TIMESTAMPTZ | No | Timestamp of last modification |

**Indexes**:
- `ix_kg_nodes_ws_type` on `(workspace_id, node_type)`
- `ix_kg_nodes_ws_ext` on `(workspace_id, external_id)`
- `ix_kg_nodes_user_ws` on `(user_id, workspace_id)`

---

### 2.2 `knowledge_graph_edges`
Represents a directed relationship between two nodes:

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | No | Primary Key |
| `user_id` | UUID | No | Foreign Key (`users.id` ON DELETE CASCADE) |
| `workspace_id` | UUID | No | Foreign Key (`workspaces.id` ON DELETE CASCADE) |
| `source_node_id` | UUID | No | Foreign Key (`knowledge_graph_nodes.id` ON DELETE CASCADE) |
| `target_node_id` | UUID | No | Foreign Key (`knowledge_graph_nodes.id` ON DELETE CASCADE) |
| `relationship_type` | VARCHAR(50) | No | Relationship type enum string |
| `confidence` | FLOAT | No | Edge confidence score in `[0.0, 1.0]` (default: 1.0) |
| `properties` | JSON | Yes | Edge properties / weights (capped at 64 KB) |
| `created_at` | TIMESTAMPTZ | No | Timestamp of creation |
| `updated_at` | TIMESTAMPTZ | No | Timestamp of last modification |

**Constraints & Indexes**:
- Unique constraint `uq_kg_edges_src_tgt_rel` on `(source_node_id, target_node_id, relationship_type)`
- `ix_kg_edges_ws_user` on `(workspace_id, user_id)`
- `ix_kg_edges_src_type` on `(source_node_id, relationship_type)`
- `ix_kg_edges_tgt_type` on `(target_node_id, relationship_type)`

---

## 3. Node & Relationship Types

### Node Types (`NodeType`)
- `USER`
- `WORKSPACE`
- `DOCUMENT`
- `DOCUMENT_CHUNK`
- `PROJECT`
- `SKILL`
- `CONVERSATION`
- `MEMORY`
- `TASK`
- `AGENT`

### Relationship Types (`RelationshipType`)
- `OWNS`
- `BELONGS_TO`
- `PART_OF`
- `RELATED_TO`
- `CONTAINS`
- `MENTIONS`
- `REFERENCES`
- `HAS_MEMORY`
- `ASSIGNED_TO`
- `EXECUTED`
- `USES`
- `DEPENDS_ON`
- `CREATED_BY`
- `WORKS_ON`

---

## 4. Graph Traversal & Safety Controls

Traversal is performed using Breadth-First Search (BFS) initialized from a list of starting node IDs:

```
[Start Nodes]
     │
     ├── Level 1: Outgoing & Incoming Edges (Tenant Bound)
     │       └── Filter by Relationship / Node Types
     ├── Level 2: Adjacencies (Visited Set check to prevent cycles)
     └── Up to max_depth (clamped to max 5, default 3)
```

### Safety Guardrails
1. **Cycle Detection**: Traversed node IDs and edge IDs are stored in a `visited` set to prevent circular reference loops.
2. **Depth Clamping**: Hard cap between `1` and `5` hops (`min(max(1, max_depth), 5)`).
3. **Result Cap**: Total returned nodes capped at `500` nodes per request to prevent memory exhaustion.
4. **Metadata Size Limit**: Metadata and properties payloads are restricted to a maximum of 64 KB (65,536 bytes).

---

## 5. Integration with Documents, Memory & RAG

### 5.1 Document Graph Synchronization
`KnowledgeGraphService.sync_document_graph(doc)` automatically maps:
- `Document` node (`external_id = doc.id`)
- `Document` -> `[BELONGS_TO]` -> `Workspace`
- `Document` -> `[CREATED_BY]` -> `User`
- `Document` -> `[CONTAINS]` -> `DocumentChunk` nodes

### 5.2 Memory Graph Synchronization
`KnowledgeGraphService.sync_memory_graph(memory)` automatically maps:
- `Memory` node (`external_id = memory.id`)
- `Memory` -> `[BELONGS_TO]` -> `User`

### 5.3 RAG Graph Context Preparation
`KnowledgeGraphService.get_graph_context(user_id, workspace_id, node_ids, max_depth=2)` retrieves adjacent entities and relationships and renders them into structured text for LLM generation:

```text
Knowledge Graph Entities:
- [DOCUMENT] specs.pdf: Technical architecture specification
- [USER] Alice: Workspace Owner

Knowledge Graph Relationships:
- specs.pdf -> [CREATED_BY] -> Alice (confidence: 1.0)
- specs.pdf -> [CONTAINS] -> Chunk 0: specs.pdf (confidence: 1.0)
```

---

## 6. REST API Reference

All endpoints require JWT Bearer authentication and respect workspace tenant context.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/knowledge-graph/nodes` | Create a new entity node |
| `GET` | `/api/v1/knowledge-graph/nodes` | List nodes with pagination and type filtering |
| `GET` | `/api/v1/knowledge-graph/nodes/{node_id}` | Retrieve node details |
| `PATCH` | `/api/v1/knowledge-graph/nodes/{node_id}` | Update node name, description, or metadata |
| `DELETE` | `/api/v1/knowledge-graph/nodes/{node_id}` | Delete node and cascade connected edges |
| `POST` | `/api/v1/knowledge-graph/edges` | Create a relationship edge between two nodes |
| `GET` | `/api/v1/knowledge-graph/edges` | List edges with relationship filtering |
| `DELETE` | `/api/v1/knowledge-graph/edges/{edge_id}` | Delete a relationship edge |
| `GET` | `/api/v1/knowledge-graph/nodes/{node_id}/neighbors` | Query 1-hop neighbors by direction |
| `POST` | `/api/v1/knowledge-graph/traverse` | Execute cycle-safe multi-hop BFS traversal |
| `GET` | `/api/v1/knowledge-graph/search` | Search nodes by substring across names/descriptions |

---

## 7. Future Neo4j Migration Possibilities

The relational graph schema in PostgreSQL / SQLite is intentionally designed to cleanly map to graph-native databases (e.g. Neo4j, AWS Neptune, or Apache AGE):
- `KnowledgeGraphNode` maps 1:1 to labeled Cypher nodes: `(:NodeType {id, name, ...})`.
- `KnowledgeGraphEdge` maps 1:1 to directed Cypher relationships: `[:RELATIONSHIP_TYPE {confidence, ...}]`.
- A migration driver can read the `knowledge_graph_nodes` and `knowledge_graph_edges` tables and construct Cypher `MERGE` statements directly into Neo4j while preserving tenant labels.
