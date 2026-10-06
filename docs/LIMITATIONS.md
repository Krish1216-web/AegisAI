# Platform Limitations, Boundary Constraints & Non-Goals

## 1. Explicit Architectural Limitations

To maintain engineering transparency, this document details the verified operational constraints, non-goals, and boundary limits of the AegisAI platform.

---

## 2. Ingestion & Document Limitations

1. **OCR / Scanned Image PDFs**:
   - The current extraction pipeline relies on text streams extracted via `pypdf`. Scanned bitmap PDF documents without an embedded OCR text layer will return empty extracted text strings.
2. **File Size & Batch Bounds**:
   - Maximum upload size per single document: **50 MB**.
   - Maximum recommended documents per workspace in local mode: **1,000 documents** before external cloud vector database clustering is advised.

---

## 3. Knowledge Graph & Vector Scaling Boundaries

1. **In-Process Vector Store Scale**:
   - Local ChromaDB indexing performs optimally up to **250,000 embedded chunks**. Beyond this threshold, migration to a distributed vector index (e.g., Qdrant, Milvus, or AWS OpenSearch) is required.
2. **Graph Traversal Hop Depth**:
   - Breadth-First Search (BFS) shortest path queries are constrained to a maximum depth of **3 hops** (`max_hops=3`) to prevent combinatorial graph explosion on dense relational clusters.

---

## 4. MCP Protocol & Subprocess Boundaries

1. **STDIO Process Confinement**:
   - STDIO subprocesses enforce a hard **45-second execution timeout**. Long-running asynchronous batch scripts should be triggered via Webhook or Message Queue rather than synchronous STDIO pipes.
2. **JSON-RPC Nesting Limits**:
   - MCP input payloads are validated up to a maximum JSON nesting depth of **10 levels** to defend against memory exhaustion and prototype pollution attacks.

---

## 5. Non-Goals

1. **Direct Foundation Model Training**: AegisAI is an orchestration and inference operating system; it does not perform raw foundational pre-training of LLM base weights.
2. **Unsandboxed Shell Access**: The platform does not allow arbitrary unvetted bash execution on host servers.
3. **Public Multi-Tenant SaaS Billing**: AegisAI currently focuses on enterprise self-hosted and private cloud deployments; multi-tenant credit card billing infrastructure (e.g., Stripe metering) is out of scope.
