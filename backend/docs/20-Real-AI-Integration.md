# Real AI Integration & Production Hardening

This document outlines the architecture, environment configurations, and security designs implemented in Phase 3.8 to support production LLM, search, and vector memory persistence.

---

## 1. Provider Configurations & Environment Settings

AegisAI resolves LLM services, search platforms, and memory indexers dynamically using centralized settings.

### Centralized Variables (.env)
```ini
# ENVIRONMENT Flags: 'dev' | 'prod' | 'test'
ENVIRONMENT=prod

# LLM Core API Keys
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=AIzaSy...
ANTHROPIC_API_KEY=xkeys-c3-...

# Centralized LLM Selection
DEFAULT_AI_PROVIDER=openai
DEFAULT_AI_MODEL=gpt-4o-mini

# Search API Key
TAVILY_API_KEY=tvly-...

# Centralized Embedding configurations
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# Providers Mappings
MEMORY_PROVIDER=postgres
RESEARCH_PROVIDER=tavily
```

---

## 2. Dynamic Memory & pgvector Architecture

The persistent memory backend relies on the `agent_memories` PostgreSQL table integrated with `pgvector` for semantic cosine similarity lookups.

### Fallback Mechanism for Local Development / CI
Production environments require a PostgreSQL database with the `vector` extension and the python `pgvector` library. 
To facilitate seamless local development and automated unit testing:
1. **Model Fallback**: If the `pgvector` library is missing, the SQLAlchemy model dynamically compiles the `embedding` column as a standard `sa.JSON` data block.
2. **Migration Fallback**: The Alembic migration verifies the active database engine dialect. If SQLite, it avoids PostgreSQL extensions and constraint ALTER commands, compiling columns cleanly.
3. **Algorithm Fallback**: If `pgvector` is inactive or SQLite is in use, semantic search queries retrieve the tenant's memory pool and sort them using a pure Python **cosine similarity** formula:
   $$\text{similarity} = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|}$$

---

## 3. Web Research & Citation Security

The Tavily search provider resolves web contents asynchronously. It preserves retrieval metadata including urls, titles, publishers, and relevance scores.

### Research Security Gates
1. **Untrusted Data Isolation**: Web search contents are treated as *untrusted raw data* inside system prompts. Strict prompt instructions prevent LLMs from executing injected instructions (e.g. prompt injection payloads like *"Ignore all previous instructions"*).
2. **No Fabricated Citations**: The `ResponseGeneratorAgent` executes a deterministic validation gate, matching every final citation's `source_id` against the list of actual sources returned by the `ResearchProvider`. Fabricated citations immediately trigger a workflow rejection (`FAIL`).

---

## 4. Critic Deterministic Hardening

The `CriticAgent` serves as a secure, deterministic gate. AI output recommendations cannot override system policies:
- **Tenant Isolation**: Critic validates that all memory records, prompt identifiers, and tool results strictly match the user and workspace of the execution context. Any mismatch forces a `FAIL` decision.
- **Unconfirmed Tool Runs**: If high-risk tools are scheduled but confirmation is pending (`REQUIRES_CONFIRMATION`), Critic immediately rejects the execution.
- **Permission Guard**: Mismatched permissions or tool execution failures force `FAIL` routing.

---

## 5. Response Generator Sanitization

The `ResponseGeneratorAgent` sanitizes all output content to prevent leakage of internal stack traces, API keys, database connection strings, Redis keys, or authentication tokens.

```python
# Content is passed through a central sanitization regex filter:
res.content = sanitize_sensitive_data(res.content)
```

---

## 6. Real-time Event Streaming (SSE)

During execution, graph nodes push completion state updates to a dedicated Redis list queue `aegis:stream:{execution_id}`.
The SSE generator polls this list and streams safe events:
- `EXECUTION_STARTED`
- `ORCHESTRATOR_STARTED`
- `PLANNER_STARTED`
- `RESEARCH_STARTED`
- `MEMORY_STARTED`
- `TOOL_STARTED`
- `TOOL_COMPLETED`
- `CRITIC_STARTED`
- `RESPONSE_GENERATING`
- `EXECUTION_COMPLETED`

---

## 7. Testing & Verification

Execute the test suite containing persistence, rate limits, locks, security overrides, and fallbacks:
```bash
python -m pytest backend/tests
```
