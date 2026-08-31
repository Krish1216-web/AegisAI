# AegisAI Document UI Integration

## 1. Overview
Phase 4.6 replaces all mock and static document data in the frontend with production-grade backend API integration. The Document Hub (`/user/documents`) enables users to securely upload, inspect, monitor, download, reindex, and delete enterprise files with real-time extraction metrics and chunk inspection.

---

## 2. Architecture & Component Structure

```
frontend/src/
├── api/
│   ├── client.ts              # Core fetch wrapper with JWT injection & 401 refresh queue
│   └── documents.ts           # Strongly typed Document API bindings & response interfaces
└── pages/user/
    └── UserDocuments.jsx      # Documents Hub dashboard, upload dropzone, registry list & chunk viewer
```

---

## 3. Strongly Typed API Client (`frontend/src/api/documents.ts`)

| Function | Method & Path | Description |
|---|---|---|
| `uploadDocument(file)` | `POST /documents/upload` | Uploads file via `multipart/form-data` |
| `listDocuments(status, limit, offset)` | `GET /documents` | Fetches workspace document registry |
| `getDocumentDetails(documentId)` | `GET /documents/{document_id}` | Retrieves document metadata and telemetry |
| `deleteDocument(documentId)` | `DELETE /documents/{document_id}` | Soft deletes database record & removes file |
| `downloadDocument(documentId)` | `GET /documents/{document_id}/download` | Fetches binary blob for browser download |
| `processDocument(documentId)` | `POST /documents/{document_id}/process` | Queues background text extraction & chunking |
| `getDocumentStatus(documentId)` | `GET /documents/{document_id}/status` | Queries real-time extraction & chunking metrics |
| `listDocumentChunks(documentId, limit, offset)` | `GET /documents/{document_id}/chunks` | Lists semantic chunks for a document |
| `getDocumentChunk(documentId, chunkId)` | `GET /documents/{document_id}/chunks/{chunk_id}` | Retrieves raw content of a specific chunk |
| `reindexDocument(documentId)` | `POST /documents/{document_id}/reindex` | Wipes vectors and re-executes embedding pipeline |

---

## 4. Key UI Capabilities

### 4.1 Drag-and-Drop Upload Dropzone
- Accessible file picker and drag-and-drop zone.
- Supports all platform-approved formats: `.pdf, .docx, .pptx, .xlsx, .txt, .csv, .jpg, .jpeg, .png, .webp, .wav, .mp3, .mp4`.
- Frontend validation rejects files exceeding 50 MB before network transmission.
- Duplicate submission prevention during active uploads.
- Clear error notifications for domain exceptions (`DUPLICATE_DOCUMENT`, `UNSUPPORTED_FILE_TYPE`, `DOCUMENT_TOO_LARGE`).

### 4.2 Document Registry & Filters
- Real-time search by filename and original filename.
- Status filtering dropdown (`ALL`, `UPLOADED`, `PROCESSING`, `READY`, `FAILED`).
- Responsive item cards with file size, creation date, and status badges.
- Loading skeletons, empty state, and retryable error state.

### 4.3 Active Document Workspace
- Telemetry metrics: File size, page/slide count, extracted character count, and total chunk count.
- **Live Status Polling**: Polling loop checks `/api/v1/documents/{document_id}/status` every 2.5 seconds while document is in `PROCESSING`, `CHUNKING`, or `EMBEDDING` states. Automatically terminates when reaching `READY` or `FAILED`.
- Visual progress bar reflecting chunk-embedding percentage.

### 4.4 Chunk Inspector & Viewer
- Displays partitioned semantic chunks with token counts, character lengths, page numbers, and section titles.
- Clicking any chunk opens the **Chunk Inspector Modal**, presenting full text with safe plain text rendering (zero raw HTML injection).

### 4.5 Document Actions & Confirmation Modals
- **Download**: Streams file blob directly into browser download with original filename.
- **Process**: Triggers background extraction for `UPLOADED` or `FAILED` documents.
- **Reindex**: Prompts a safety confirmation modal before regenerating chunks and embeddings.
- **Delete**: Prompts a safety confirmation modal before soft-deleting document record and removing storage file.

---

## 5. Security & Tenant Boundaries
- **JWT Context**: Authentication is managed by `client.ts`, which injects the Bearer token into all requests.
- **Workspace Isolation**: User and workspace IDs are never accepted from client inputs; the backend resolves tenant scope from the verified JWT.
- **XSS Protection**: All chunk text and document properties are rendered as plain string nodes, guarding against arbitrary script execution in parsed documents.

---

## 6. Verification Results

- **Frontend Production Build**: Built cleanly with Vite in 1.34s (0 TypeScript / build errors).
- **Backend Test Suite**: 153 unit tests passing (`pytest tests/unit/`).
