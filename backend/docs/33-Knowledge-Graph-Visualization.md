# AegisAI — Phase 5.7: Production Knowledge Graph Visualization

## Overview
Phase 5.7 upgrades the Knowledge Graph Explorer into an interactive, production-grade visual exploration engine integrated directly with live multi-tenant backend APIs, real-time node & edge inspectors, debounced entity search, multi-hop shortest-path discovery, and memory synchronization.

---

## 1. Graph Explorer Architecture

- **Canvas & Simulation Engine**:
  - Force-directed simulation with real-time repulsive force, spring link tension, center gravitational pull, and velocity damping.
  - Interactive panning, mouse-wheel/button zooming ($0.25\times - 3.0\times$), view centering, and physics toggle.
  - Interactive node dragging with boundary constraints.

---

## 2. Visual Design & Semantic Styling

- **Node Types**: Distinct badge colors, background glows, and borders for all 9 canonical types (`PROJECT`, `SKILL`, `DOCUMENT`, `DOCUMENT_CHUNK`, `USER`, `ORGANIZATION`, `TASK`, `AGENT`, `MEMORY`).
- **Edge Representations**: Directed arrowheads, labeled relationship types (`USES`, `CONTAINS`, `DEPENDS_ON`, `REFERENCES`, `ASSIGNED_TO`, `WORKS_ON`, `RELATED_TO`), and confidence-proportional line weights.
- **Interactive State**:
  - *Selection State*: Pulsing selection halo, highlighting 1-hop connected neighbors, and dimming unrelated entities.
  - *Path Highlighting*: Emerald glow on path nodes and edges, displaying exact hop count and ordered traversal steps.

---

## 3. Filtering & Search Controls

- **Node Type Filter**: Filter canvas elements by specific node category or view all.
- **Relationship Type Filter**: Filter graph by active relationship types.
- **Confidence Slider**: Interactive threshold slider ($0.0 - 1.0$) to filter out low-confidence relationships.
- **Isolated Node Toggle**: Option to hide nodes without active edges.
- **Debounced Enhanced Search**: Real-time autocomplete searching against `/api/v1/knowledge-graph/search/enhanced` with jump-to-node camera centering.

---

## 4. Inspector & Multi-Hop Tools

- **Node Inspector**: Displays ID, external ID, degree of connections, descriptions, and provenance metadata (`document_id`, `chunk_id`, `memory_id`).
- **Dynamic Neighbor Expansion**: "Expand Neighbors" fetches adjacent nodes on-demand from `/api/v1/knowledge-graph/nodes/{node_id}/neighbors` and merges them dynamically without duplication.
- **Pathfinder Modal**: Multi-hop shortest-path search using `/api/v1/knowledge-graph/path` with visual graph highlighting.
- **Graph Context Modal**: Formatted markdown context preview and one-click copy tool using `/api/v1/knowledge-graph/context`.
- **Memory Sync Integration**: Sync graph entities directly into Agent Memory via `/api/v1/knowledge-graph/nodes/{node_id}/sync-memory`.
