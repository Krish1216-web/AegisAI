# Document Processing Architecture

The AegisAI document processing pipeline runs text extraction, normalization, security checks, and metadata mapping inside background task executions.

## 1. Lifecycle Status Transitions
A document goes through the following transitions:
- **UPLOADED**: Initial status after file upload.
- **PROCESSING**: Triggered by requesting `POST /api/v1/documents/{id}/process`.
- **PROCESSED**: Set on success. Extracted metrics (`page_count`, `word_count`, `character_count`) and normalization output length are saved.
- **FAILED**: Set on exception. A safe error statement is persisted into the database record.

## 2. Component Design
```
┌──────────────────────┐      ┌─────────────────────────┐      ┌────────────────────────┐
│     FastAPI Router   │ ───► │  BackgroundTasks Queue  │ ───► │DocumentProcessingServ. │
└──────────────────────┘      └─────────────────────────┘      └────────────────────────┘
                                                                           │
                                                                           ▼
                                                               ┌────────────────────────┐
                                                               │ExtractorFactory Resolv.│
                                                               └────────────────────────┘
                                                                           │
                                                                           ▼
                                                               ┌────────────────────────┐
                                                               │  Specific Extractor    │
                                                               └────────────────────────┘
                                                                           │
                                                                           ▼
                                                               ┌────────────────────────┐
                                                               │ Text Normalizer & Scan │
                                                               └────────────────────────┘
                                                                           │
                                                                           ▼
                                                               ┌────────────────────────┐
                                                               │ Commit to PostgreSQL   │
                                                               └────────────────────────┘
```
- **FastAPI Endpoint**: Receives the request and immediately returns a `202 Accepted` status with status `"PROCESSING"`, scheduling the background job.
- **Temporary Isolation**: The worker downloads binary bytes into a thread-safe local temporary file, limiting RAM footprint for large files.
- **Factory Resolution**: Dynamically maps extension/MIME headers to the optimal parser engine.
- **Status Updates**: Writes state back to the database at start, finish, or fail event boundaries.
