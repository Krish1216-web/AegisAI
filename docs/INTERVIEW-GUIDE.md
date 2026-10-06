# AegisAI — Technical Interview & Recruiter Defense Guide

This guide prepares engineers for discussing AegisAI in high-level software engineering, AI engineering, and systems architecture interviews.

---

## 🎯 High-Frequency Interview Questions

### 1. Why did you build AegisAI?
> *"I built AegisAI to solve the enterprise adoption bottleneck for autonomous AI. While conversational LLMs are impressive, businesses cannot deploy raw chatbots for mission-critical workflows because they suffer from context amnesia, unverified hallucinations, un-sandboxed API tools, lack of tenant isolation, and zero auditability. AegisAI treats AI as an auditable, governed operating system that combines multi-agent planning, vector memory, knowledge graphs, standardized MCP tools, and cryptographic audit chains."*

### 2. What was the hardest engineering challenge you faced?
> *"The hardest challenge was building a fault-tolerant multi-agent coordination engine with cyclic verification. Coordinating 9 specialized agents executing parallel subtasks via `asyncio.gather` while preventing deadlocks and infinite replanning loops required implementing Kahn's algorithm for topological sorting and bounded exponential backoff. Additionally, ensuring that intermediate claims were rigorously fact-checked by a Critic Agent against retrieved vector chunks without adding excessive latency required sub-millisecond in-memory cache layers in Redis."*

### 3. How does memory differ from RAG in AegisAI?
> *"Memory and RAG serve two distinct cognitive functions:*
> - **Memory Vault** stores user-specific, session-level, and conversational preferences and state (e.g., 'User prefers concise executive tables'). It combines an ephemeral Redis buffer with long-term vector embeddings subjected to exponential time-decay scoring.
> - **Enterprise RAG** operates over static or updated corporate document repositories (PDFs, Word docs, Markdown specs), performing sliding-window semantic chunking, dense vector retrieval, and verbatim citation offset mapping."*

### 4. How do you prevent tool abuse and security breaches in MCP?
> *"We enforce Defense in Depth for Model Context Protocol (MCP) integrations:*
> 1. **SSRF Mitigation**: Outbound DNS resolution checks block private RFC 1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) and loopback addresses.
> 2. **STDIO Sandboxing**: Local subprocesses execute with non-root privileges, parameterized argument arrays, and hard 45-second execution timeouts.
> 3. **Human Approval Gates**: High-risk tool calls (e.g., database mutations or payment calls) trigger an interactive cryptographic confirmation request requiring team maintainer sign-off."*

### 5. How is tenant isolation enforced across the stack?
> *"Tenant isolation is enforced strictly at every layer:*
> - **Ingress**: The authenticated JWT claim provides the immutable `workspace_id`.
> - **Relational DB**: All SQLAlchemy ORM queries append mandatory `filter(Model.workspace_id == workspace_id)` clauses.
> - **Vector Database**: Metadata filters enforce `where={"workspace_id": active_workspace}` on every similarity query.
> - **Cache & Redis**: All keys are prefixed with `ws:{workspace_id}:{session_id}`."*

### 6. How does the system defend against Indirect Prompt Injection?
> *"When documents or third-party tool outputs are ingested, they are treated as untrusted data. We seal untrusted context inside strict XML delimiters (`<untrusted_document_context>`) with system prompt directives instructing the LLM to treat the content purely as passive data. Furthermore, the Critic Agent evaluates final answers against source citations, catching unauthorized command executions."*

### 7. Why did you implement a Knowledge Graph alongside Vector RAG?
> *"Vector RAG is excellent for unstructured semantic search, but it struggles with multi-hop relational queries (e.g., 'Which services depend on the authentication gateway owned by Team Alpha?'). Our Knowledge Graph represents relational triples (`subject, predicate, object`) and executes Breadth-First Search (BFS) shortest-path pathfinding to resolve explicit entity connections that dense vectors miss."*

### 8. What are the key performance optimizations in your frontend?
> *"We split a monolithic 1.48 MB bundle down to an entry JS size of **100.20 kB (23.14 kB gzip)**—a **93.2% size reduction**—using Vite dynamic route lazy loading (`React.lazy`) and dedicated vendor chunks (`vendor-flow`, `vendor-charts`, `vendor-react`). We also implemented WCAG-oriented keyboard focus trapping in slide-over drawers and debounced search filters to eliminate unnecessary React re-renders."*
