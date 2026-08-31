# Phase 4.2 Audit - Document Processing & Text Extraction

## 1. Existing Document Model
- The `Document` model defined in `backend/app/models/document.py` contains core fields needed:
  - `page_count` (Integer)
  - `duration_seconds` (Float)
  - `width` (Integer)
  - `height` (Integer)
  - `extracted_text_length` (Integer)
  - `processing_error` (String)
  - `meta_data` (JSON, mapped to column `"metadata"`)
- Storing extra extraction metrics (e.g. `word_count`, `character_count`, `language`, timestamps) inside `meta_data` JSON avoids unnecessarily altering the DB schema.

## 2. Existing Storage Flow
- `DocumentStorage` at `backend/app/services/document_storage.py` handles reading files securely using traversal-resistant boundaries.
- Stored files are structured as `workspaces/<workspace_id>/documents/<document_id>/original_file`.

## 3. Existing Status Fields
- `status` field defaults to `"UPLOADED"`.
- Valid status transitions for processing will be:
  - `UPLOADED` -> `PROCESSING`
  - `PROCESSING` -> `PROCESSED` (on success)
  - `PROCESSING` -> `FAILED` (on error)

## 4. Existing APIs
- `/api/v1/documents` endpoints handle upload, details, list, delete, and download.
- Currently, no route exists under `POST /api/v1/documents/{document_id}/process` or `GET /api/v1/documents/{document_id}/status`.

## 5. Reusable Authentication / Tenant Logic
- Endpoint tenant protection utilizes:
  - `get_current_user` for identity context.
  - `get_workspace_member(workspace_id, user, db)` to assert membership.
  - Ownership is verified by matching `document.user_id == current_user.id`.

## 6. Missing Processing Functionality
- Extractor classes (PDF, DOCX, PPTX, XLSX, TXT, CSV, Image, Audio/Video).
- Text normalizer for whitespace/newlines.
- Security scanner (Prompt injection patterns).
- `POST /api/v1/documents/{document_id}/process` (with background processing support).
- `GET /api/v1/documents/{document_id}/status`.
