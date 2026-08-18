# Document Chunking and Embeddings (Phase 4.3)

AegisAI segments processed documents into token-aware, logical text blocks and maps them to high-dimensional embedding vectors for semantic indexing.

## 1. Chunking Architecture
```
Processed Document
        ↓
Extracted Normalized Text
        ↓
Recursive Character Splitting (Headings, Paragraphs, Newlines, Words)
        ↓
Token Boundary Sizing Validation (CHUNK_SIZE = 1000, OVERLAP = 150)
        ↓
Deduplication & Reuse Verification (via content_hash + model mapping checks)
        ↓
Batch Embedding Provider Calls
        ↓
PostgreSQL pgvector Vector Storage
```

## 2. Configurable Settings
Configuration parameters reside in `config.py` and are managed through `.env` bindings:
- `CHUNK_SIZE`: Token capacity per segment (default: 1000).
- `CHUNK_OVERLAP`: Overlapping token margin between segments (default: 150).
- `EMBEDDING_PROVIDER`: Selected backend engine (`mock` | `openai` | `gemini`).
- `EMBEDDING_MODEL`: Provider embedding model (default: `text-embedding-3-small`).
- `EMBEDDING_DIMENSION`: Target embedding length dimension (default: 1536).
- `EMBEDDING_BATCH_SIZE`: Vector execution batch sizes (default: 32).

## 3. Database Schema
Table: `document_chunks`
- `id` (UUID): Primary Key.
- `document_id` (UUID): Reference to parent document.
- `user_id` / `workspace_id` (UUID): Multi-tenant isolation attributes.
- `chunk_index` (Integer): Segment position index.
- `content` (Text): The raw normalized chunk text.
- `content_hash` (String): SHA-256 string representation of content for reuse checks.
- `token_count` / `character_count` (Integer): Segment metrics.
- `page_number` / `section_title` (Nullable): Source position citations.
- `embedding` (Vector/JSON): High-dimensional vector float lists.
- `embedding_model` / `embedding_dimension` (String/Integer): Generation signatures.
- `metadata` (JSON): Citation properties.

## 4. Idempotency & Batch Optimization
- **Batch Deduplication**: Identical text blocks within the same document processing batch only trigger a single external provider call, copying the response vector array to all matching chunk objects.
- **Persistent Reuse**: Compares the target `content_hash` and `embedding_model` against existing database chunk tables. If a match is found, the existing vector is reused directly.

## 5. Background Execution Pipeline
1. **UPLOADED**: Initial document state.
2. **PROCESSING**: Running text extracts and normalization checks.
3. **CHUNKING**: Deconstructing file into logical chunks and saving schemas.
4. **EMBEDDING**: Interacting with provider endpoints to fetch vector arrays.
5. **READY**: Pipeline complete. Chunks and embeddings are fully persistent.
6. **FAILED**: Catching errors safely.

## 6. Endpoints
- `POST /api/v1/documents/{document_id}/chunk` — Start background chunking.
- `GET /api/v1/documents/{document_id}/chunks` — Fetch chunks. Omit vector array weights.
- `GET /api/v1/documents/{document_id}/chunks/{chunk_id}` — View specific chunk details.
- `POST /api/v1/documents/{document_id}/reindex` — Safely clear chunks and re-run.
