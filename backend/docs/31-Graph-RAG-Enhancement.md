# AegisAI — Phase 5.5: Graph + RAG Enhancement

## Overview
Phase 5.5 connects Entity Resolution and validated Relationship Edges into the Hybrid RAG engine (`HybridRAGService`), creating a unified retrieval and multi-agent reasoning flow.

---

## 1. Retrieval & Context Pipeline

```
User Prompt
     ↓
Query Entity Extraction (QueryEntityExtractor)
     ↓
Entity Resolution against Workspace Graph (EntityResolver)
     ↓
Multi-Hop Graph Context & Edge Discovery (KnowledgeGraphIntelligenceService)
     ↓
Vector Similarity Retrieval + Chunk Provenance Boost (VectorRetriever)
     ↓
Hybrid Score Fusion & Deduplication (HybridScoreFusion)
     ↓
Conflict Detection & Context Formatting (HybridContextBuilder)
     ↓
LLM Grounded Answer Synthesis (RAGGenerationFlow)
     ↓
Critic Safety Verification & Attributed Citations
```

---

## 2. Evidence Separation & Budgeting
- **Separated Sections**:
  - `=== DOCUMENT EVIDENCE ===`: Factual chunk snippets with document names, page numbers, and relevance scores.
  - `=== KNOWLEDGE GRAPH TOPOLOGY ===`: Hierarchical tree representing connected entities, node types, and relationship edges.
- **Budget Allocation**: $70\%$ allocated to document evidence, $30\%$ to graph topology.

---

## 3. Fallback & Citation Integrity
- Document citations link directly to real `document_id`, `chunk_id`, and `page_number`.
- Graph citations link directly to real `node_id`, entity name, and `relationship_type`.
- When both vector and graph evidence are empty, returns safe fallback without fabricating citations.
