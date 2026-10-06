# Changelog — AegisAI

All notable changes to the **AegisAI** platform are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] - Phase 12.12 Final Documentation & Polish

### Added
- **Definitive Engineering Knowledge Package (`docs/`)**: Comprehensive technical architecture specifications for Multi-Agent Orchestration, Vector Memory, Enterprise RAG, Knowledge Graph, MCP Integration, Visual Workflows, Governance, and Threat Modeling.
- **Interactive Showcase & Demo Mode (`/showcase`)**: 6 fully orchestrated real-time simulation tours with speed controls, linear plain-text outlines, and strict non-dismissible demo indicator banners.
- **Root Documentation**: Production `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `CHANGELOG.md`.
- **Systematic UI/UX Polish**: Cross-platform responsive layouts, WCAG 2.1 AA accessible navigation, dark/light theme persistence, and dynamic bundle splitting.

### Verified
- **1,178 Total Local Automated Tests**: 955 backend pytest suites (100% pass) and 223 frontend vitest suites (100% pass).
- **Frontend Production Bundle**: Reduced primary entry chunk to 100.20 kB (23.14 kB gzip) with dynamic vendor and route splitting.

---

## [1.0.0-rc1] - 2026-10-01 — Phase 11 Deployment & Phase 12 Product Architecture

### Added
- **Phase 12.1 — Enterprise Design System**: CSS variables, dark/light tokens, high-contrast states, responsive typography, and standardized badge/button primitives.
- **Phase 12.2 — Intelligence Factory & Landing Tour**: Interactive product landing page, feature station tours, architectural flowcharts, and quick navigation.
- **Phase 12.3 — AI OS Workspace**: Unified execution terminal, multi-agent status strips, plan inspection drawers, real-time SSE stream listeners, and citation drawers.
- **Phase 12.4 — Agent Center**: 9-agent capability catalog, side-by-side agent comparison drawer, DAG architecture flow, and live agent telemetry counters.
- **Phase 12.5 — Memory Vault**: Dual-tier vector memory inspector, similarity threshold sliders, working memory session viewer, and eviction controls.
- **Phase 12.6 — MCP Center**: Multi-transport tool hub (SSE, HTTP, STDIO, WS), JSON schema validator, test execution modal, and human confirmation gating.
- **Phase 12.7 — Visual AI Automation Studio**: Drag-and-drop ReactFlow workflow canvas, node configuration panels, cycle detection, execution logs, and approval queue.
- **Phase 12.8 — Enterprise Knowledge Intelligence Center**: Multi-file document upload, semantic chunking viewer, hybrid RAG search, 2D/3D force-directed knowledge graph, and BFS shortest-path reasoning.
- **Phase 12.9 — Enterprise Governance & Control Center**: RBAC management, team memberships, SHA-256 tamper-evident audit ledger, security posture gauges, and compliance report exports.
- **Phase 12.10 — Performance & Accessibility**: React `lazy()` code splitting, dynamic imports, ARIA live regions, focus trapping in drawers, skip-to-content links, and keyboard navigation.
- **Phase 12.11 — Demo / Showcase Mode**: 6 scripted enterprise scenarios with step-by-step execution playback, presentation mode, and zero interference with production state.
- **Phase 11 — Production Deployment Architecture**: Multi-stage Dockerfiles, Docker Compose (Dev, Staging, Prod), Nginx reverse proxy with TLS 1.3, Redis caching, Celery/scheduler background workers, Prometheus metrics, and automated disaster recovery runbooks.

---

## [0.9.0] - 2026-09-20 — Phase 9 & 10 Enterprise Security & Team Collaboration

### Added
- Multi-user team workspace collaboration with fine-grained role assignments (`owner`, `maintainer`, `editor`, `viewer`).
- Real-time collaborative activity feed and WebSocket notification broadcasting.
- Comprehensive security audit: Rate limiting, CORS policy tightening, SSRF protection for MCP servers, AES-256 encryption for stored API keys, and SHA-256 audit chaining.
- Automated fuzzing and boundary test suites for API gateway endpoints.

---

## [0.8.0] - 2026-08-30 — Phase 8 Platform Core Intelligence Engine

### Added
- Unified platform execution engine with 9 canonical agents.
- Real-time SSE streaming for multi-agent state changes (`VALIDATING`, `PLANNED`, `EXECUTING`, `VERIFYING`, `COMPLETED`).
- Critic agent automated evaluation of response factuality against retrieved RAG and Knowledge Graph evidence chunks.
- Response synthesizer with markdown rendering and interactive footnote citation chips.
