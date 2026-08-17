# Document Upload Architecture

The document upload pipeline is structured as follows:

```
[Multipart Form-Data Request] 
            │
            ▼
┌───────────────────────┐
│     FileValidator     │  ◄── Check size (<50MB) and MIME format
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│    Workspace Check    │  ◄── Ensure JWT user belongs to targeted workspace
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│   Duplicate Check     │  ◄── Verify SHA-256 checksum is unique for tenant
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│    DocumentStorage    │  ◄── Securely save as 'original_file' (no traversal)
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│   Database Register   │  ◄── Commit Document record + metadata to PostgreSQL
└───────────────────────┘
```
