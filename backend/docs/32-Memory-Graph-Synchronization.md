# AegisAI — Phase 5.6: Graph + Memory Synchronization

## Overview
Phase 5.6 introduces a production-ready, bidirectional, loop-protected synchronization layer between AegisAI's `AgentMemory` system and the tenant-isolated `KnowledgeGraph`.

---

## 1. Synchronization Flow

```
Memory Record (AgentMemory / MemoryRecord)
     ↓
Entity Mention Extraction (QueryEntityExtractor)
     ↓
Canonical Entity Resolution (EntityResolver)
     ↓
Tenant Graph Node Creation / Resolution
     ↓
Contextual Edge Establishment (User Anchor → Target Node)
     ↓
Provenance & Sync Origin Metadata Attachment
     ↓
RAG & Multi-Agent Reasoning Integration
```

---

## 2. Bidirectional Loop Protection
To prevent continuous ping-pong recursion (`Memory` $\to$ `Graph` $\to$ `Memory` $\to$ `Graph`):
- `MemoryGraphSyncService.sync_memory_to_graph` inspects `meta_data["sync_origin"]`. If set to `"graph_to_memory"`, graph propagation is safely skipped.
- `MemoryGraphSyncService.sync_graph_to_memory` inspects `meta_data["sync_origin"]`. If set to `"memory_to_graph"`, memory creation is skipped.

---

## 3. Idempotency & Conflict Handling
- Repeated synchronization of identical memory items updates relationship confidence and timestamps without creating duplicate nodes or edges.
- Contradictory assertions maintain separate evidence chains and attach `conflict_indicators` rather than silently overwriting historical facts.

---

## 4. Provenance-Aware Cleanup
When a memory record is deleted:
- Incident edges dedicated to the specific `memory_id` are cleanly removed.
- Nodes retain their canonical status if backed by other document chunks or memory records, while removing the deleted `memory_id` from their `meta_data["provenance"]` list.

---

## 5. API Endpoints
- `POST /api/v1/knowledge-graph/sync/memory/{memory_id}`: Triggers memory $\to$ graph synchronization.
- `POST /api/v1/knowledge-graph/nodes/{node_id}/sync-memory`: Triggers graph node $\to$ memory synchronization.
