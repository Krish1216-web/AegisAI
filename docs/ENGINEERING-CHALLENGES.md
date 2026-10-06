# AegisAI — Engineering Challenges & Technical Trade-Offs

This document details the genuine engineering obstacles encountered during the design and implementation of **AegisAI**, explaining why each was difficult, the implemented technical approach, and the associated trade-offs.

---

## 1. Multi-Agent Coordination & Deadlock Prevention

### The Challenge
Coordinating 9 specialized agents in parallel asynchronous pipelines (`asyncio.gather`) created risks of circular task dependencies, race conditions during state mutations, and unconstrained replanning loops when the Critic Agent rejected intermediate candidate answers.

### Implemented Approach
- **Topological DAG Ordering**: The Planner Agent outputs an explicit dependency graph parsed with **Kahn's Algorithm** to detect and reject cycles before dispatch.
- **Bounded Verification Loops**: The Orchestrator enforces a hard maximum of 3 critic retry cycles. If confidence remains below 0.85 after 3 attempts, the pipeline falls back to conservative synthesis with explicit evidence gap notices.

### Engineering Trade-Off
- *Trade-off*: Rejecting cycles and enforcing a 3-retry cap prevents deadlocks and infinite LLM token burn, but it prevents the system from exploring complex circular deliberation chains autonomously.

---

## 2. Server-Side Request Forgery (SSRF) in Dynamic MCP Tools

### The Challenge
The Model Context Protocol (MCP) enables autonomous agents to connect dynamically to external servers over HTTP/SSE/WebSocket. A malicious prompt or poisoned document could instruct an agent to query internal cloud infrastructure (e.g., `http://169.254.169.254/latest/meta-data/` on AWS) to exfiltrate private credentials.

### Implemented Approach
- **Pre-Connection DNS Resolution & IP Filtering**: Before opening sockets, hostnames are resolved to IP addresses via asynchronous DNS lookup.
- **Strict Network Prohibitions**: Any address falling into RFC 1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.1`), or link-local ranges (`169.254.0.0/16`) is rejected immediately and logged as a security violation.

### Engineering Trade-Off
- *Trade-off*: Blocking private IP ranges protects internal infrastructure, but local development environments require explicit `MCP_SSRF_ALLOWLIST` entries if interacting with local test servers.

---

## 3. Memory & Relational Knowledge Synchronization (`MemoryGraphSync`)

### The Challenge
Vector embeddings provide excellent semantic similarity recall, but fail on multi-hop relational pathfinding (e.g., "Which servers are impacted if Gateway X is offline?"). Maintaining two separate knowledge systems (Vector Store + Knowledge Graph) risked data divergence where facts existed in vector memory but not in the graph.

### Implemented Approach
- **Automated Memory-to-Graph Bridge**: When a high-confidence factual assertion is memorized, an asynchronous background worker extracts structured `(subject, predicate, object)` triples and commits them to the Knowledge Graph.
- **Deduplication & Edge Weighting**: Existing triples matching `(workspace_id, subject, predicate)` have their edge weights and timestamps updated rather than creating duplicate redundant nodes.

### Engineering Trade-Off
- *Trade-off*: Entity extraction adds a small background processing overhead (~50–100ms per memory insert) to guarantee cross-paradigm knowledge consistency.

---

## 4. Cryptographic Audit Chain Performance & Concurrency

### The Challenge
Creating an immutable SHA-256 hash chain ($H_n = \text{SHA256}(H_{n-1} \,\|\, \text{payload})$) for every administrative mutation and high-risk agent execution introduces potential database serialization bottlenecks under concurrent user writes.

### Implemented Approach
- **Optimistic Concurrency & Lock Sequencing**: Audit records use database-level sequential IDs with transactional row locking on the head block ($H_{n-1}$) during hash computation, ensuring deterministic chain continuity.
- **In-Memory Verification Caching**: Chain verification queries check recent block windows and perform incremental hash audits rather than re-hashing million-record tables on every read.

### Engineering Trade-Off
- *Trade-off*: Sequential row locking slightly limits concurrent audit writes to ~1,500 operations/sec on standard PostgreSQL, which is more than sufficient for enterprise administrative events while guaranteeing cryptographic non-repudiation.

---

## 5. Frontend Bundle Optimization & Accessibility

### The Challenge
Integrating interactive canvas frameworks (`@xyflow/react`), data visualization libraries (`Chart.js`, `recharts`), and rich icon sets resulted in an initial monolithic bundle size exceeding 1.48 MB, causing slow first paint times.

### Implemented Approach
- **Dynamic Code Splitting**: Applied `React.lazy()` to all primary application routes and configured manual vendor chunk isolation in Vite (`vendor-flow`, `vendor-charts`, `vendor-react`).
- **Entry JS Reduction**: Reduced entry bundle size to **100.20 kB (23.14 kB gzip)**—a **93.2% size reduction**.
- **WCAG-Oriented Focus Management**: Engineered native JavaScript focus trapping in slide-over drawers with escape key restoration and ARIA live regions for SSE execution streams.

### Engineering Trade-Off
- *Trade-off*: Route-level lazy loading requires graceful `Suspense` fallback skeletons, but results in near-instantaneous initial application load.
