# AegisAI — Phase 5.4: Relationship Extraction

## Overview
Phase 5.4 implements relationship extraction, validation, and semantic edge persistence between resolved Knowledge Graph nodes.

---

## 1. Supported Relationship Types
All extracted relationships map to the canonical `RelationshipType` enum:
- `USES`
- `DEPENDS_ON`
- `CONTAINS`
- `PART_OF`
- `REFERENCES`
- `ASSIGNED_TO`
- `WORKS_ON`
- `RELATED_TO`
- `CREATED_BY`
- `BELONGS_TO`
- `MENTIONS`
- `OWNS`

---

## 2. Extraction & Validation Rules
- **Non-null & Distinct Nodes**: Self-loops (`source.id == target.id`) are rejected.
- **Tenant Isolation**: Both source and target nodes must belong to the active `workspace_id` and `user_id`.
- **Contradiction Detection**: Flags inverse or contradictory cyclic assertions (e.g. mutual `CONTAINS` or opposing dependency claims) and stores indicators in `meta_data["conflict_indicators"]`.
- **Confidence Bounding**: Relationship confidence is bounded within $[0.1, 1.0]$.

---

## 3. Duplicate Edge Prevention
- Identified by `(workspace_id, user_id, source_node_id, target_node_id, relationship_type)`.
- If an edge already exists, updates to the higher confidence score and enriches metadata/provenance rather than creating duplicate edges.
