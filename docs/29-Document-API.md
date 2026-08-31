# Document Hub API

All endpoints reside under `/api/v1/documents`.

### 1. Upload Document
- **Endpoint**: `POST /api/v1/documents/upload`
- **Body**: `multipart/form-data` with field `file`
- **Response**: `DocumentUploadResponse`
- **Throws**:
  - `400 Bad Request` if file type unsupported or corrupt signature
  - `409 Conflict` if duplicate checksum found

### 2. List Documents
- **Endpoint**: `GET /api/v1/documents`
- **Params**: `status` (optional), `limit` (default: 10), `offset` (default: 0)
- **Response**: `List[DocumentListItemResponse]`

### 3. Get Details
- **Endpoint**: `GET /api/v1/documents/{document_id}`
- **Response**: `DocumentDetailsResponse`

### 4. Delete Document
- **Endpoint**: `DELETE /api/v1/documents/{document_id}`
- **Response**: `204 No Content`

### 5. Download Document
- **Endpoint**: `GET /api/v1/documents/{document_id}/download`
- **Response**: Binary stream
