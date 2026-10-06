# Configuration Reference & Environment Variables

## 1. Overview

AegisAI configuration is managed via environment variables and loaded via Pydantic Settings (`app.core.config.Settings`).

---

## 2. Core Server & Environment Settings

| Variable Name | Type | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | `string` | `development` | Environment tier: `development`, `staging`, `production`. |
| `DEBUG` | `boolean` | `false` | Enable verbose tracebacks (Must be `false` in production). |
| `SECRET_KEY` | `string` | `CHANGE_ME_IN_PROD` | 256-bit encryption key used for JWT signing and session keys. |
| `BACKEND_CORS_ORIGINS` | `list` | `["http://localhost:5173"]` | Allowlisted frontend origin domains for CORS headers. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `int` | `30` | Expiration lifetime for JWT access tokens. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `int` | `7` | Expiration lifetime for cryptographic refresh tokens. |

---

## 3. Database, Cache & Vector Stores

| Variable Name | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/aegisai_db` | Asynchronous PostgreSQL connection string. |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL for caching, sessions, and pub/sub. |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | Disk directory for ChromaDB dense vector store indices. |

---

## 4. Multi-Agent & LLM Providers

| Variable Name | Default Value | Description |
| :--- | :--- | :--- |
| `DEFAULT_LLM_PROVIDER` | `openai` | Primary LLM provider (`openai`, `anthropic`, `ollama`). |
| `OPENAI_API_KEY` | `""` | OpenAI API key for embeddings and completions. |
| `ANTHROPIC_API_KEY` | `""` | Anthropic API key for Claude completions. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endpoint for local offline LLM model inference. |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Default 1536-dimensional embedding model name. |

---

## 5. RAG, Memory & MCP Engine Guardrails

| Variable Name | Default Value | Description |
| :--- | :--- | :--- |
| `RAG_CHUNK_SIZE` | `500` | Target character length for document semantic chunks. |
| `RAG_CHUNK_OVERLAP` | `100` | Sliding window character overlap for document chunks. |
| `RAG_SIMILARITY_THRESHOLD` | `0.72` | Minimum cosine similarity score for retrieved RAG chunks. |
| `MEMORY_SESSION_TTL_SECONDS`| `86400` | TTL duration for ephemeral working memory (24 hours). |
| `MCP_SUBPROCESS_TIMEOUT` | `45` | Hard process timeout in seconds for STDIO MCP tool executions. |
| `MCP_SSRF_ALLOWLIST` | `[]` | Explicit domain/IP allowlist overriding private IP blocks. |

---

## 6. Verification & Security Rules

> [!WARNING]
> **Production Verification Checklist**:
> 1. In `production`, `DEBUG` must be `false`.
> 2. `SECRET_KEY` must be a high-entropy string generated with `openssl rand -hex 32`.
> 3. `BACKEND_CORS_ORIGINS` must not contain wildcard `*`.
