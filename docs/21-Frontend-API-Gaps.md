# Frontend-Backend API Gaps

This document catalogues the AegisAI frontend features that remain mocked due to the absence of corresponding backend endpoints in the `/api/v1` router path.

---

## 1. Catalog of API Gaps

### MCP Marketplace (`UserMcpMarket.jsx`)
- **UI Capability**: Scan, configure, and install model context server plugins (GitHub, Slack, Google Drive).
- **Backend status**: No endpoints exist for `/api/v1/mcp` configuration.

### Documents Hub (`UserDocuments.jsx`)
- **UI Capability**: Upload files (PDFs, docs), compile table extractions, and index documents.
- **Backend status**: No endpoints exist for `/api/v1/documents`.

### Workflow Builder (`UserWorkflows.jsx`)
- **UI Capability**: n8n-style grid interface to add, drag, link, and compile triggers/planner nodes.
- **Backend status**: No endpoints exist for `/api/v1/workflows`.

### Memory Center (`UserMemory.jsx`)
- **UI Capability**: Scanning, pinning, and deleting vector memory categories and tags.
- **Backend status**: Postgres Vector provider is active on the backend but no external API path exists for `/api/v1/memory` CRUD operations.

### Knowledge Graph (`UserGraph.jsx`)
- **UI Capability**: Interactive node visualization mapping entity relationships.
- **Backend status**: No endpoints exist for `/api/v1/graph`.

### Reports Compiler (`UserReports.jsx`)
- **UI Capability**: Weekly system audits, memory growths, and doc compilation downloads.
- **Backend status**: No endpoints exist for `/api/v1/reports`.

---

## 2. Integration Status

| Component | Status | Route Prefix |
| :--- | :--- | :--- |
| **Authentication** | Real Connected | `/auth` |
| **AI Workspace Chat** | Real Connected | `/agent/execute` |
| **Active Execution Queue** | Real Connected | `/agent/executions` |
| **MCP Market** | Mocked | — |
| **Documents Hub** | Mocked | — |
| **Workflow Builder** | Mocked | — |
| **Memory Explorer** | Mocked | — |
| **Knowledge Graph** | Mocked | — |
| **Reports Compiler** | Mocked | — |
