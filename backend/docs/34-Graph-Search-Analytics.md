# AegisAI — Phase 5.8: Graph Search & Analytics

## Overview
Phase 5.8 implements a production-grade Graph Search and Analytics layer on top of AegisAI's Knowledge Graph, providing deterministic explainable relevance ranking, structural connectivity metrics, health diagnostics, orphan node detection, duplicate candidate identification, and interactive UI visual analytics.

---

## 1. Architecture & Capabilities

```
Knowledge Graph Database
     ↓
GraphAnalyticsService
     ├── Analytics Overview (Nodes, Edges, Degree, Density, Provenance)
     ├── Health Diagnostics (Status, Orphan Rate, Conflicts, Warnings)
     ├── Hub Connectivity (Top N Connected Entities)
     ├── Orphan Isolation (Entities with Zero In/Out Edges)
     ├── Duplicate Review (Normalized Key & String Similarity Candidates)
     └── Advanced Search (Exact, Prefix, Partial, Fuzzy + Connectivity Boost)
     ↓
REST API Endpoints (/api/v1/knowledge-graph/analytics/* & /search/advanced)
     ↓
Knowledge Graph Explorer UI & Analytics Modal
```

---

## 2. Deterministic Search Ranking
Search queries are evaluated in deterministic priority order:
1. **Exact Match on Name** (`score = 1.0 + connectivity_boost`)
2. **Prefix Match on Name** (`score = 0.85 + connectivity_boost`)
3. **Substring Match on Name** (`score = 0.70 + connectivity_boost`)
4. **Substring Match on Description** (`score = 0.50 + connectivity_boost`)
5. **Fuzzy String Similarity** (`score = ratio * 0.60 + connectivity_boost`)
- **Connectivity Boost**: $+ \min(0.15, \text{degree} \times 0.015)$ to elevate highly relevant hub nodes.

---

## 3. Structural & Health Diagnostics
- **Graph Metrics**: Total Nodes, Total Edges, Average Degree, Max Degree, Density, and Average Confidence.
- **Provenance Breakdown**: Classifies entity origin (`document`, `memory`, `system`).
- **Health Classification**:
  - `HEALTHY`: Well-connected graph with high average confidence and low orphan rate.
  - `WARNING`: Moderate orphan rate ($>25\%$), low-confidence edges ($<0.60$), or detected semantic contradictions.
  - `CRITICAL`: Severe structural degradation ($>50\%$ orphan rate in graphs with $>10$ nodes).
- **Duplicate Review**: Detects potential duplicates using normalized alphanumeric keys and `difflib.SequenceMatcher` without destructive automatic merges.

---

## 4. REST Endpoints
- `GET /api/v1/knowledge-graph/analytics/overview`
- `GET /api/v1/knowledge-graph/analytics/health`
- `GET /api/v1/knowledge-graph/analytics/top-connected?limit=10`
- `GET /api/v1/knowledge-graph/analytics/orphans?limit=50`
- `GET /api/v1/knowledge-graph/analytics/duplicates?similarity_threshold=0.85`
- `POST /api/v1/knowledge-graph/search/advanced`
