# AegisAI — Comprehensive Viva Presentation & Defense Guide

This guide is prepared for final-year project evaluations, academic vivas, and technical defense examinations.

---

## 🎙️ Spoken Presentation Scripts

### 30-Second Elevator Pitch
> *"Good morning, examiners. My project is AegisAI, an enterprise autonomous multi-agent AI Operating System. Traditional AI applications act as simple chat wrappers that suffer from context loss, hallucinations, and unverified tool execution. AegisAI solves this by providing a governed execution platform combining 9 specialized agents in a Directed Acyclic Graph, dual-tier vector memory, hybrid document RAG, relational knowledge graph reasoning, standardized Model Context Protocol tool execution, visual workflow automation, and a cryptographic SHA-256 tamper-evident audit ledger. The platform is verified with 1,178 automated tests passing at 100%."*

### 1-Minute Executive Overview
> *"AegisAI is designed to bridge the gap between generative AI models and enterprise mission-critical software. While standard LLM interfaces are stateless and prone to ungrounded claims, AegisAI organizes intelligence into a modular 8-stage execution pipeline. When a user submits a query, our Planner Agent constructs a task DAG, delegating parallel subtasks to specialized RAG, Knowledge Graph, Memory, and Tool Executor agents. Before any response is delivered, a dedicated Critic Agent evaluates the factuality of the evidence against source chunks to prevent hallucinations. The entire system is strictly tenant-isolated, governed by dual-tier RBAC, and records every action in a cryptographic SHA-256 hash chain."*

### 3-Minute Architecture Walkthrough
> *"Let's look at the architectural topology of AegisAI. The platform is organized into four distinct tiers:*
> 1. *Client Tier: Built on React 19, featuring an Intelligence Factory workspace, a drag-and-drop workflow canvas, and an interactive showcase simulator with an entry bundle size of just 100 kB.*
> 2. *Security & Ingress Gateway: FastAPI handles asynchronous requests, extracts workspace tenant context from verified JWT claims, and evaluates dual-tier RBAC combining system roles with team roles.*
> 3. *Platform Execution Engine: Coordinates a canonical workforce of 9 specialized agents. The Orchestrator manages state transitions, the Planner creates task DAGs, and parallel subtasks retrieve document chunks, traverse knowledge graph triples via BFS, and call sandboxed MCP tools.*
> 4. *Persistence & Governance Tier: Integrates PostgreSQL for relational models, Redis for caching and locks, pgvector/ChromaDB for 1536-dimensional embeddings, and an append-only SHA-256 cryptographic audit ledger.*
> *This design ensures that every AI response is evidence-backed, reproducible, and fully auditable."*

---

## 🎯 40+ Technical Viva Questions & In-Depth Answers

### Category 1: System Architecture & Design (Questions 1–5)

#### Q1: What is the architectural difference between AegisAI and a standard ChatGPT wrapper?
- **Short Answer**: A chat wrapper sends a prompt directly to a single LLM API and prints the response. AegisAI is an operating platform that decomposes queries into task DAGs, queries vector memory and knowledge graphs, validates evidence with a Critic Agent, executes sandboxed MCP tools, and records actions in a cryptographic audit chain.
- **Deep Answer**: A wrapper is stateless and single-threaded. AegisAI implements a multi-agent state machine (`REQUESTED` $\to$ `VALIDATING` $\to$ `PLANNED` $\to$ `EXECUTING` $\to$ `VERIFYING` $\to$ `COMPLETED`). It executes parallel asynchronous subtasks (`asyncio.gather`), checks evidence consistency using cosine similarity and factuality thresholds ($\ge 0.85$), and strictly isolates tenant data by `workspace_id`.

#### Q2: Why did you choose FastAPI over Flask or Django for the backend?
- **Short Answer**: FastAPI provides native Python asynchronous `async`/`await` support, high throughput, automatic Pydantic v2 data validation, and built-in Server-Sent Events (SSE) streaming.
- **Deep Answer**: Multi-agent orchestration requires non-blocking concurrency to run RAG vector searches, Knowledge Graph queries, and external MCP tool calls in parallel. FastAPI's ASGI event loop natively handles concurrent I/O without thread blocking.

#### Q3: How does the platform handle real-time streaming to the frontend?
- **Short Answer**: Using Server-Sent Events (SSE) and WebSockets.
- **Deep Answer**: When an execution is initiated via `POST /api/v1/platform/execute`, the endpoint yields an `EventSourceResponse` streaming granular state updates (`step_started`, `step_progress`, `step_completed`) directly to the React client, avoiding costly client polling loops.

#### Q4: How is multi-tenant isolation enforced in AegisAI?
- **Short Answer**: Every database entity, vector search query, memory record, and workflow is strictly scoped by `workspace_id`.
- **Deep Answer**: The authenticated JWT contains an immutable `workspace_id` claim. Repository queries in SQLAlchemy append `filter(Model.workspace_id == workspace_id)`, vector queries in ChromaDB/pgvector apply `$where: {workspace_id: ...}`, and Redis keys use `ws:{workspace_id}:{session_id}` prefixes.

#### Q5: What is the purpose of the Critic Agent?
- **Short Answer**: To eliminate hallucinations by verifying candidate answers against retrieved evidence chunks.
- **Deep Answer**: The Critic Agent compares generated statements against extracted document chunks and knowledge graph triples, calculating a factuality score (0.0 to 1.0). If the score falls below 0.85, the Critic formulates a targeted critique and triggers a replanning loop (up to 3 retries).

---

### Category 2: Multi-Agent Coordination & Planning (Questions 6–10)

#### Q6: How does the Planner Agent generate the execution DAG?
- **Short Answer**: It parses user intent, identifies necessary agent capabilities, and outputs an acyclic dependency graph of subtasks.
- **Deep Answer**: The Planner analyzes the prompt against registered tools, documents, and memory. It produces a JSON DAG specifying `task_id`, `agent_target`, `dependencies`, and `parameters`. The DAG is validated for acyclicity using Kahn's algorithm before dispatch.

#### Q7: How do agents communicate with each other?
- **Short Answer**: Through structured JSON message schemas coordinated by the central Orchestrator.
- **Deep Answer**: Rather than allowing unconstrained peer-to-peer chatter, all agent communication is mediated by the Orchestrator. Intermediate outputs are written to an ephemeral execution scratchpad in Redis and passed to downstream dependent nodes as typed Pydantic payloads.

#### Q8: What happens if an individual agent subtask fails during execution?
- **Short Answer**: The Orchestrator captures the exception, attempts retry with fallback parameters, or returns a partial verified result.
- **Deep Answer**: Each task runs within an `asyncio` error boundary. If an MCP tool or external RAG search fails, the exception is logged to telemetry, and the Critic decides whether remaining evidence is sufficient for synthesis or if a fallback agent should be invoked.

#### Q9: How does the system prevent infinite agent replanning loops?
- **Short Answer**: By enforcing a hard maximum retry limit of 3 cycles.
- **Deep Answer**: The Orchestrator maintains a `retry_count` in the execution context. If the Critic rejects the output 3 times, the loop terminates and the Synthesizer outputs a conservative response acknowledging missing evidence.

#### Q10: What are the 9 specialized agents in AegisAI?
- **Short Answer**: Orchestrator, Planner, Research, Memory, Enterprise RAG, Graph Reasoning, Tool Executor, Critic, and Response Synthesizer.
- **Deep Answer**: Each agent encapsulates a specialized system prompt, dedicated schema validators, and scoped tool permissions, separating concerns between planning, retrieval, reasoning, execution, critique, and synthesis.

---

### Category 3: Memory Vault & Semantic Retrieval (Questions 11–15)

#### Q11: What is the difference between Ephemeral Working Memory and Long-Term Memory?
- **Short Answer**: Working memory stores the active conversational sliding window in Redis (TTL: 24h), while Long-Term Memory stores durable dense vector embeddings in pgvector/ChromaDB.
- **Deep Answer**: Working memory provides rapid sub-millisecond access to the last 20 conversation turns. Long-Term Memory persists high-importance user preferences and factual assertions as 1536-dimensional embeddings queried via cosine similarity.

#### Q12: How does memory decay scoring work?
- **Short Answer**: It reduces the relevance of older memories over time while prioritizing frequently accessed facts.
- **Deep Answer**: Relevance is computed as: $\text{Score} = \alpha \cdot \text{CosineSim}(\vec{q}, \vec{m}) + (1 - \alpha) \cdot e^{-\lambda \Delta t}$. This balances semantic similarity with temporal freshness.

#### Q13: What is `MemoryGraphSync`?
- **Short Answer**: An automated bridge that converts memorized text facts into structured Knowledge Graph triples.
- **Deep Answer**: When a memory record is created, an entity extraction worker identifies `(subject, predicate, object)` triples and commits them to the Knowledge Graph, ensuring vector and relational memory remain synchronized.

#### Q14: How does AegisAI prevent memorizing sensitive PII or passwords?
- **Short Answer**: Automated regex and entropy filters reject sensitive patterns before committing to vector memory.
- **Deep Answer**: The memory service passes text through a sensitive data filter. Matches against API key patterns (`sk-...`, `Bearer ...`), credit cards, or passwords raise `SensitiveMemoryRejected` and are blocked from persistence.

#### Q15: Can a user manually delete their stored memories?
- **Short Answer**: Yes, via the Memory Vault UI (`/user/memory`) or REST API.
- **Deep Answer**: Users have full CRUD control over their memories. Deleting a memory removes its vector record from the index and soft-deletes the database record.

---

### Category 4: Enterprise RAG & Document Processing (Questions 16–20)

#### Q16: What document formats are supported by the RAG ingestion pipeline?
- **Short Answer**: PDF, DOCX, TXT, and Markdown (`.md`).
- **Deep Answer**: Extraction is handled asynchronously: `pypdf` for PDF page and layout parsing, `python-docx` for Word tables and paragraphs, and UTF-8 decoders for text and markdown.

#### Q17: What chunking strategy is implemented?
- **Short Answer**: Semantic sliding-window chunking (500 characters with 100 character overlap).
- **Deep Answer**: Rather than arbitrary fixed-byte cuts, the chunker snaps to sentence terminators (`.`, `?`, `!`, `\n\n`) to preserve semantic coherence across chunk boundaries.

#### Q18: How is citation provenance tracked?
- **Short Answer**: Each chunk retains metadata containing `document_id`, `page_number`, and character start/end offsets.
- **Deep Answer**: When the Synthesizer outputs references, it attaches structured citation metadata. In the UI, clicking a citation footnote opens the Evidence Drawer displaying the exact excerpt and document page.

#### Q19: What is Hybrid Search in AegisAI?
- **Short Answer**: Combining dense vector semantic search with sparse keyword (BM25) search.
- **Deep Answer**: Dense search captures semantic meaning, while sparse search captures exact acronyms and error codes. Results are merged using Reciprocal Rank Fusion (RRF).

#### Q20: How does AegisAI protect against indirect prompt injection in uploaded files?
- **Short Answer**: Document context is isolated inside strict XML delimiters (`<untrusted_document_context>`), and system prompts instruct agents to treat content as passive data.
- **Deep Answer**: Unvetted text is sealed within explicit delimiters. The LLM system prompt enforces that text within delimiters cannot alter system instructions. Furthermore, the Critic Agent evaluates whether actions were triggered by unauthorized document instructions.

---

### Category 5: Knowledge Graph & Relational Reasoning (Questions 21–25)

#### Q21: What data model represents the Knowledge Graph?
- **Short Answer**: Relational triples consisting of `Subject`, `Predicate`, and `Object`.
- **Deep Answer**: Each triple has a unique ID, workspace ID, confidence score, weight, and JSONB property bag for metadata (e.g., source document, timestamp).

#### Q22: How does the Breadth-First Search (BFS) pathfinder work?
- **Short Answer**: It finds the shortest relational path between two entities up to a maximum depth of 3 hops.
- **Deep Answer**: BFS traverses the graph adjacency list layer by layer, tracking visited nodes to avoid cyclic loops. It returns an ordered path of triples explaining the relational connection between origin and target.

#### Q23: Why limit graph traversal to 3 hops?
- **Short Answer**: To prevent combinatorial explosion and excessive query latency on dense graphs.
- **Deep Answer**: In dense relational graphs, branching factors grow exponentially ($O(b^d)$). Restricting $d \le 3$ guarantees sub-50ms query times while answering 95%+ of enterprise relational queries.

#### Q24: How is the knowledge graph rendered in the frontend?
- **Short Answer**: Using a 2D/3D force-directed canvas with D3 and Canvas API.
- **Deep Answer**: Nodes represent entities (color-coded by type) and edges represent predicates. The visualizer supports zoom, pan, node inspection drawers, and accessible linear text fallback outlines.

#### Q25: How are orphan entities handled in the graph?
- **Short Answer**: Graph analytics algorithms detect and report isolated nodes with zero degree centrality.
- **Deep Answer**: The Graph Analytics service calculates in-degree, out-degree, and density metrics, providing health reports to administrators via `/api/v1/graph/analytics`.

---

### Category 6: Model Context Protocol (MCP) & Tools (Questions 26–30)

#### Q26: What is the Model Context Protocol (MCP)?
- **Short Answer**: An open standard developed by Anthropic allowing LLMs to discover and interact with external tools, prompts, and resources.
- **Deep Answer**: MCP standardizes tool definitions and execution over structured JSON-RPC 2.0 messages, eliminating the need for brittle custom API integrations.

#### Q27: What 4 transports does AegisAI support for MCP?
- **Short Answer**: Server-Sent Events (SSE), Streamable HTTP, STDIO (subprocess), and WebSocket.
- **Deep Answer**: SSE for streaming cloud tools, HTTP for REST endpoints, STDIO for isolated local CLI processes, and WebSocket for persistent bidirectional sessions.

#### Q28: How does AegisAI prevent Server-Side Request Forgery (SSRF) in MCP?
- **Short Answer**: Outbound requests undergo DNS resolution and IP filtering blocking private and loopback addresses.
- **Deep Answer**: Target URLs are resolved to IP addresses before connecting. Any IP matching RFC 1918 ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), `127.0.0.1`, or `169.254.169.254` is immediately rejected.

#### Q29: How does Human-in-the-Loop (HITL) approval work for MCP tools?
- **Short Answer**: High-risk tools pause execution until an authorized team member approves the action in the UI.
- **Deep Answer**: Tools flagged with `HIGH` or `CRITICAL` risk tiers create an approval record with a 300-second timeout. The user interface prompts maintainers for confirmation; once signed, execution resumes.

#### Q30: How are STDIO MCP tool subprocesses sandboxed?
- **Short Answer**: Executed with non-root privileges, parameterized argument arrays, and a hard 45-second timeout.
- **Deep Answer**: Commands are invoked via `asyncio.create_subprocess_exec` without shell expansion (`shell=False`), preventing shell injection attacks. If execution exceeds 45s, `SIGKILL` is sent automatically.

---

### Category 7: Visual Workflows & Automation (Questions 31–35)

#### Q31: What library powers the Visual Workflow Studio?
- **Short Answer**: `@xyflow/react` (ReactFlow).
- **Deep Answer**: It provides a highly customizable SVG canvas supporting custom node types, dynamic edge connections, mini-maps, and interactive controls.

#### Q32: What 8 node primitives exist in the workflow engine?
- **Short Answer**: Trigger, Agent, Tool (MCP), Condition, Router, Transform, Approval, and Webhook.
- **Deep Answer**: Each node encapsulates distinct execution semantics: Trigger handles ingress, Agent executes AI subtasks, Tool calls MCP, Condition/Router evaluate branching expressions, Transform maps JSON payloads, Approval pauses for human sign-off, and Webhook handles egress.

#### Q33: How does the workflow validator detect cycles?
- **Short Answer**: Using Kahn's Algorithm for topological sorting.
- **Deep Answer**: Kahn's algorithm computes in-degrees for all nodes. If the algorithm cannot resolve all nodes into an ordered list, a cycle is present and workflow execution is blocked.

#### Q34: How are workflow variables passed between nodes?
- **Short Answer**: Through an immutable execution context using scoped JSONPath expressions.
- **Deep Answer**: Nodes reference upstream values via syntax like `{{node_1.output.summary}}`. The runner immutably merges outputs into the step context, ensuring parallel branches do not cause race conditions.

#### Q35: How does workflow versioning work?
- **Short Answer**: Workflows use semantic versioning (`v1`, `v2`, `v3`) with atomic snapshots.
- **Deep Answer**: Editing an active workflow creates a new version draft. Any currently running executions continue against their original version snapshot without interruption.

---

### Category 8: Security, Governance, Testing & Operations (Questions 36–42)

#### Q36: How does the SHA-256 tamper-evident audit ledger guarantee integrity?
- **Short Answer**: Each audit entry incorporates the hash of the preceding entry in its own cryptographic hash calculation.
- **Deep Answer**: For entry $n$: $\text{Hash}_n = \text{SHA256}(\text{Hash}_{n-1} \,\|\, \text{Timestamp} \,\|\, \text{WorkspaceID} \,\|\, \text{UserID} \,\|\, \text{Action} \,\|\, \text{PayloadJSON})$. If any historical database row is altered, subsequent hash checks fail, identifying the exact tampering point.

#### Q37: How is Dual-Tier RBAC implemented?
- **Short Answer**: By combining System Roles (`super_admin`, `admin`, `user`) with Team Roles (`owner`, `maintainer`, `editor`, `viewer`).
- **Deep Answer**: Permissions are resolved hierarchically: system admins have global bypass within their workspace, while team members' effective permissions are computed based on team role memberships.

#### Q38: How are third-party API keys stored securely?
- **Short Answer**: Encrypted at rest using AES-256-GCM.
- **Deep Answer**: The `CredentialStore` encrypts sensitive connection strings and API keys using AES-256-GCM with unique initialization vectors (IVs) per record. Keys are never logged in plaintext.

#### Q39: What is the verified test coverage of AegisAI?
- **Short Answer**: 1,178 total verified tests passing at 100% (955 backend Pytest tests and 223 frontend Vitest tests).
- **Deep Answer**: Backend tests verify unit isolation, multi-agent state machines, MCP transports, SSRF filters, and audit chains. Frontend tests verify accessibility, focus traps, theme switching, and component state flows.

#### Q40: How is frontend bundle performance optimized?
- **Short Answer**: Dynamic route lazy loading and vendor chunk isolation reduced entry JS to 100.20 kB (23.14 kB gzip).
- **Deep Answer**: Vite splits heavy libraries into isolated chunks: `@xyflow/react` (166 kB), Chart.js (386 kB), and Lucide icons (26 kB), allowing initial page load in sub-200ms.

#### Q41: How does the Showcase / Demo mode guarantee data safety?
- **Short Answer**: It operates in a pure presentation sandbox without modifying production databases.
- **Deep Answer**: Showcase scenarios use pre-scripted state steps with speed multipliers (0.5x, 1x, 2x) and persistent amber warning banners, ensuring no production data or credentials are touched.

#### Q42: What are the main limitations of the current implementation?
- **Short Answer**: Lack of automated browser-level E2E tests, dependency on text-stream PDFs (no OCR for bitmap scans), and requirement of external cloud infrastructure for multi-region S3 storage.
- **Deep Answer**: These boundaries are documented in `docs/LIMITATIONS.md` to maintain full academic and engineering transparency.
