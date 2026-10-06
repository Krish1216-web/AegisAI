# AegisAI — Engineering Documentation Index

Welcome to the central technical documentation repository for **AegisAI**, the enterprise autonomous multi-agent operating system. This index categorizes all architecture, subsystem deep-dives, operational runbooks, security models, and API specifications.

---

## 🏛️ 1. Core Architecture Specifications

| Document | Purpose | Audience |
| :--- | :--- | :--- |
| [System Architecture](file:///D:/CP/AegisAI/docs/ARCHITECTURE.md) | High-level topology, component boundaries, execution models, and data flows. | Architects, Tech Leads, Evaluators |
| [Multi-Agent Architecture](file:///D:/CP/AegisAI/docs/AGENT-ARCHITECTURE.md) | Deep dive into the 9 canonical agents, state machine, DAG decomposition, and validation loops. | AI Engineers, Researchers |
| [Memory Architecture](file:///D:/CP/AegisAI/docs/MEMORY-ARCHITECTURE.md) | Ephemeral working memory, session context, vector embeddings, and similarity retrieval. | Backend Engineers, AI Engineers |
| [Enterprise RAG Architecture](file:///D:/CP/AegisAI/docs/RAG-ARCHITECTURE.md) | Multi-format document ingestion, semantic chunking, dense vector retrieval, and verbatim citations. | AI Engineers, Search Engineers |
| [Knowledge Graph Architecture](file:///D:/CP/AegisAI/docs/KNOWLEDGE-GRAPH-ARCHITECTURE.md) | Relational triple store, shortest-path BFS traversal, and memory-graph synchronization. | Knowledge Engineers, Data Architects |
| [Model Context Protocol (MCP) Architecture](file:///D:/CP/AegisAI/docs/MCP-ARCHITECTURE.md) | Multi-transport integration (SSE, HTTP, STDIO, WS), tool discovery, schema validation, and sandboxing. | Platform Engineers, Tool Developers |
| [Visual Workflow Automation](file:///D:/CP/AegisAI/docs/WORKFLOW-ARCHITECTURE.md) | Drag-and-drop DAG workflow canvas, node lifecycles, conditional routing, human approvals, and cron scheduling. | Automation Engineers, Product Teams |
| [Enterprise Governance & RBAC](file:///D:/CP/AegisAI/docs/GOVERNANCE-ARCHITECTURE.md) | Multi-tenant isolation, dual-tier RBAC, cryptographic SHA-256 audit chains, and compliance exports. | Security Engineers, Compliance Officers |
| [End-to-End Data Flows](file:///D:/CP/AegisAI/docs/DATA-FLOWS.md) | Visual sequence diagrams and step-by-step transaction traces across all subsystems. | All Engineers, Evaluators |

---

## 🔒 2. Security, Quality & Verification

| Document | Purpose | Audience |
| :--- | :--- | :--- |
| [Security Architecture](file:///D:/CP/AegisAI/docs/SECURITY-ARCHITECTURE.md) | Defense-in-depth framework, JWT token handling, SSRF defense, prompt injection mitigations, and secret redaction. | Security Architects, Auditors |
| [STRIDE Threat Model](file:///D:/CP/AegisAI/docs/THREAT-MODEL.md) | Comprehensive STRIDE threat assessment, attack surfaces, vulnerability mitigations, and residual risks. | Security Reviewers, Compliance |
| [Testing & Quality Assurance](file:///D:/CP/AegisAI/docs/TESTING.md) | Strategy and full test inventory across 955 backend tests and 223 frontend tests (1,178 total). | QA Engineers, Developers |
| [Performance & Accessibility](file:///D:/CP/AegisAI/docs/PERFORMANCE.md) | Frontend bundle splitting, lazy loading, a11y WCAG 2.1 AA compliance, and backend async I/O benchmarks. | Frontend Engineers, UI/UX Designers |
| [Capability & Truth Matrix](file:///D:/CP/AegisAI/docs/CAPABILITY-MATRIX.md) | Exhaustive breakdown of features marked as `IMPLEMENTED`, `VERIFIED LOCALLY`, or `SIMULATED DEMO`. | Evaluators, Maintainers |
| [Platform Boundaries & Limitations](file:///D:/CP/AegisAI/docs/LIMITATIONS.md) | Explicit statement of theoretical and practical system limits, concurrency bounds, and non-supported items. | Solution Architects, DevOps |

---

## 🚀 3. Operations, Deployment & APIs

| Document | Purpose | Audience |
| :--- | :--- | :--- |
| [Production Deployment Runbook](file:///D:/CP/AegisAI/docs/DEPLOYMENT.md) | Docker Compose environments (Dev, Staging, Prod), Nginx TLS 1.3 setup, health checks, and disaster recovery. | DevOps, SREs |
| [Observability & Telemetry](file:///D:/CP/AegisAI/docs/OBSERVABILITY.md) | Prometheus metrics, OpenTelemetry traces, structured JSON logging, and SSE execution streams. | SREs, System Operators |
| [API Reference Specification](file:///D:/CP/AegisAI/docs/API.md) | REST endpoints, request/response JSON schemas, error codes, and SSE streaming protocols. | API Consumers, Frontend Devs |
| [Configuration Reference](file:///D:/CP/AegisAI/docs/CONFIGURATION.md) | Complete reference of all environment variables, connection strings, security flags, and defaults. | DevOps, Developers |
| [Local Development Guide](file:///D:/CP/AegisAI/docs/DEVELOPMENT.md) | Developer onboarding, environment setup, database migrations, seeding, and contribution workflows. | New Developers, Contributors |
| [UI Module & Route Map](file:///D:/CP/AegisAI/docs/UI-MODULE-MAP.md) | Component hierarchy, route bindings, context providers, and design token integration. | Frontend Developers |

---

## 🎨 4. Frontend & Polish Deliverables

For UI/UX design specifications and milestone reports from Phase 12, refer to:
- [Phase 12 Master Polish Summary](file:///D:/CP/AegisAI/frontend/docs/PHASE-12-FINAL-PRODUCT-POLISH.md)
- [Phase 12.11 Demo / Showcase Mode Guide](file:///D:/CP/AegisAI/frontend/docs/PHASE-12.11-DEMO-SHOWCASE-MODE.md)
- [Enterprise Design System Guide](file:///D:/CP/AegisAI/frontend/docs/DESIGN-SYSTEM.md)
- [Comprehensive UI/UX Audit Log](file:///D:/CP/AegisAI/frontend/docs/UI-UX-AUDIT.md)
