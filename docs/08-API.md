# AegisAI - REST API & WebSocket Architecture

This document details the REST API endpoints, standard JSON response models, error payload schemas, and WebSocket event names for **AegisAI**.

---

## 1. REST Endpoint Specifications

The API is versioned via URL prefixing (`/api/v1/`).

### Authentication & Sessions
- `POST /api/v1/auth/login`: Exchange user credentials for an Access Token and a Refresh Token (set as cookie).
- `POST /api/v1/auth/refresh`: Validate a Refresh Token and mint a new token pair.
- `POST /api/v1/auth/logout`: Revoke active session tokens in Redis.

### Conversation Workspaces
- `GET /api/v1/workspaces/{id}/conversations`: List active chat threads (supports pagination).
- `POST /api/v1/workspaces/{id}/conversations`: Initialize a new conversation thread.
- `GET /api/v1/conversations/{id}/messages`: Fetch message history.

### Documents & File Ingest
- `POST /api/v1/workspaces/{id}/documents/upload`: Upload file payloads for chunk parsing.
- `GET /api/v1/workspaces/{id}/documents`: List parsed assets metadata.

### Workflows & Engine Controls
- `GET /api/v1/workspaces/{id}/workflows`: List saved workflow pipelines definitions.
- `POST /api/v1/workspaces/{id}/workflows/run`: Trigger a new Celery workflow execution run.

---

## 2. Standardized Response Formats

AegisAI enforces structured response JSON envelopes across all endpoints.

### Standard Paginated Success Schema
```json
{
  "success": true,
  "data": [
    {
      "id": "conv_90a312f0",
      "title": "Audit repository config files",
      "created_at": "2026-07-31T12:00:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "per_page": 20,
    "total_records": 124,
    "total_pages": 7
  }
}
```

### Standard Error Response Schema
```json
{
  "success": false,
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "The credentials provided do not match our decryption keys.",
    "details": {
      "username": "User block is suspended."
    }
  }
}
```

---

## 3. WebSocket Event Registry

For real-time console streaming and workflow progress tracking, clients open WebSocket connections to `/api/v1/ws/workspace/{id}`.

### Outgoing Client Commands (Client -> Server)
- `agent:send_message`: Submits a new prompt query payload to the LangGraph executor.
- `workflow:stop`: Force-kills an active running workflow thread.

### Incoming System Streams (Server -> Client)
- `agent:stream_chunk`: Delivers token-by-token text streams of the running response.
- `workflow:node_started`: Notifies that a new agent station (e.g. Planning, Memory, Executor) is executing.
- `workflow:node_finished`: Outputs metrics, diagnostic logs, and execution parameters upon step completion.
- `system:alert`: Dispatches real-time security threats, rate-limit warnings, or integration failures.
