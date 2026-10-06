# AegisAI — End-to-End Data Flows & Transaction Walkthroughs

This document illustrates the complete end-to-end data flows and runtime sequence diagrams for the primary operational scenarios in **AegisAI**.

---

## 1. Platform Multi-Agent Query Execution (SSE Stream)

```mermaid
sequenceDiagram
    autonumber
    actor User as Client Application / Browser
    participant API as FastAPI Router (/api/v1/platform/execute)
    participant Auth as Auth & Tenant Context
    participant Engine as Platform Engine (Dispatcher)
    participant Planner as Planner Agent
    participant Research as RAG & Graph Agents
    participant Critic as Critic Agent
    participant Synth as Synthesizer Agent
    participant Audit as SHA-256 Audit Ledger

    User->>API: POST /api/v1/platform/execute (Prompt + JWT)
    API->>Auth: Validate JWT & Extract workspace_id
    Auth-->>API: Authorized Context
    
    API->>Engine: Initiate Execution Session
    Engine-->>API: Yield SSE { status: "VALIDATING" }
    API-->>User: Stream SSE: VALIDATING

    Engine->>Planner: Request Task DAG Decomposition
    Planner-->>Engine: Task Plan (RAG Search, Graph Traversal)
    Engine-->>API: Yield SSE { status: "PLANNED", plan: [...] }
    API-->>User: Stream SSE: PLANNED

    Engine-->>API: Yield SSE { status: "EXECUTING" }
    API-->>User: Stream SSE: EXECUTING

    par Subtask 1: Enterprise RAG
        Engine->>Research: Dense Vector Similarity Search
        Research-->>Engine: 3 Document Chunks with Citations
    and Subtask 2: Graph Traversal
        Engine->>Research: Multi-Hop BFS Pathfinding
        Research-->>Engine: 2 Relational Triples
    end

    Engine-->>API: Yield SSE { status: "VERIFYING" }
    API-->>User: Stream SSE: VERIFYING

    Engine->>Critic: Fact-Check Evidence & Cross-Validate
    Critic-->>Engine: Verification Score: 0.96 (Pass)

    Engine->>Synth: Assemble Formatted Markdown & Citations
    Synth-->>Engine: Structured Markdown Response

    Engine->>Audit: Append Tamper-Evident SHA-256 Audit Link
    Audit-->>Engine: Hash Recorded (H_n)

    Engine-->>API: Yield SSE { status: "COMPLETED", result: {...} }
    API-->>User: Stream SSE: COMPLETED + Response Payload
```

---

## 2. Document Ingestion & Semantic Chunking Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as Enterprise User
    participant UI as Knowledge Center UI
    participant API as Documents API (/api/v1/documents/upload)
    participant Storage as File Storage / S3
    participant Parser as Extraction Pipeline
    participant Chunker as Sliding-Window Chunker
    participant Embedder as Embedding Model (1536-dim)
    participant VectorDB as Vector Database (ChromaDB)

    User->>UI: Selects PDF / DOCX File
    UI->>API: Multipart Form POST /api/v1/documents/upload
    API->>API: Validate MIME, File Size (<50MB) & Workspace Quota
    API->>Storage: Save Raw Document Bytes
    
    API->>Parser: Trigger Extraction Worker
    Parser->>Parser: Extract Text & Page Structure
    Parser->>Chunker: Stream Raw Text
    
    Chunker->>Chunker: Segment into 500-char chunks (100-char overlap)
    Chunker->>Embedder: Batch Embed Chunks
    Embedder-->>Chunker: 1536-dim Vector Arrays
    
    Chunker->>VectorDB: Upsert Vectors with Workspace Metadata
    VectorDB-->>API: Indexing Complete (N chunks indexed)
    
    API-->>UI: 201 Created { document_id, chunk_count, status: "READY" }
    UI->>User: Renders Document in Knowledge Catalog
```

---

## 3. Governed MCP Tool Execution with Human Confirmation

```mermaid
sequenceDiagram
    autonumber
    actor Agent as Tool Executor Agent
    participant MCP as MCP Supervisor
    participant Security as Security & SSRF Filter
    participant Approval as Human Approval Hub
    actor Admin as Authorized Team Maintainer
    participant Server as External MCP Server (SSE / STDIO)

    Agent->>MCP: Request Tool Call: "execute_sql_mutation"
    MCP->>Security: Validate Target Host & Tool Risk Tier
    Security-->>MCP: High Risk Action Detected

    MCP->>Approval: Create Pending Approval (Timeout: 300s)
    Approval-->>Admin: Notification Broadcast (WebSocket)
    
    Admin->>Approval: POST /api/v1/workflows/approvals/{id}/decision (APPROVE)
    Approval-->>MCP: Approval Confirmed by Maintainer

    MCP->>Server: Dispatch JSON-RPC Request over Transport
    Server-->>MCP: Tool Execution Result
    
    MCP-->>Agent: Return Verified Tool Artifact
```
