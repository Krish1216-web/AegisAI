# AegisAI — Phase 5.3: Entity Resolution

## Overview
Phase 5.3 implements a production-grade Entity Resolution engine that deterministically maps raw entity mentions extracted from document chunks and user prompts to canonical Knowledge Graph nodes, preventing duplicate node creation across re-indexing runs while enforcing strict multi-tenant boundaries.

---

## 1. Matching Strategy Hierarchy

The `EntityResolver` evaluates matching strategies in strict precedence order:

1. **Exact Canonical Match**: Exact case-insensitive matching after whitespace and punctuation normalization (`confidence = 1.0`).
2. **Alias Dictionary Match**: Resolves recognized engineering aliases (e.g. `postgres` $\to$ `PostgreSQL`, `k8s` $\to$ `Kubernetes`, `fast-api` $\to$ `FastAPI`, `lang graph` $\to$ `LangGraph`) (`confidence = 0.98`).
3. **Normalized Key Match**: Alphanumeric stripped lookup keys (`EntityNormalizer.get_lookup_key`) for identical canonical representations (`confidence = 0.95`).
4. **Type-Aware Validation**: Enforces type compatibility (e.g. distinguishing a `TASK` from a `SKILL` with identical names).
5. **Controlled Fuzzy Similarity**: Type-aware string similarity via `difflib.SequenceMatcher` (threshold $\ge 0.88$, `confidence = ratio`).
6. **New Node Insertion**: Creates a new canonical node if no criteria are met.

---

## 2. Duplicate Prevention & Provenance Tracking
- When an entity mention resolves to an existing node, its provenance list in `meta_data["provenance"]` is enriched with the current `document_id`, `chunk_id`, `page_number`, and `section_title`.
- Rich descriptions and observed aliases are preserved without overwriting existing data.

---

## 3. Safe Node Merging
- `EntityResolver.merge_duplicate_nodes(user_id, workspace_id, source_id, target_id)`:
  - Reroutes inbound and outbound edges from `source_id` to `target_id`.
  - Combines aliases, descriptions, and provenance arrays.
  - Deletes the redundant source node within tenant bounds.

---

## 4. Multi-Tenant Security
- All database queries, resolutions, and merges strictly enforce `user_id` and `workspace_id` from the authenticated JWT session.
