# Frontend-Backend Integration

This document outlines the client-server integration architecture implemented in Phase 3.9 of AegisAI.

---

## 1. Frontend Architecture
The frontend is a React SPA powered by Vite, styling with TailwindCSS, and routing via `HashRouter` (`react-router-dom`). It communicates with the FastAPI backend over HTTP using a central request client.

---

## 2. Backend API Architecture
The backend is built with FastAPI, executing with PostgreSQL database persistence and Redis cache structures:
- **Authentication**: JWT verification, refresh cookie rotation.
- **Agent Executions**: LangGraph workflow pipelines, PostgreSQL checkpoints, Redis distributed locks, and Server-Sent Events (SSE).

---

## 3. Authentication & JWT Flow
1. **Login**: User submits username & password to `POST /auth/login`. Returns access token (`access_token`) and sets HTTP-Only `refresh_token` cookie.
2. **Session Persistence**: Access token is stored in frontend `localStorage`. Every request injects `Authorization: Bearer <token>` header.
3. **Session Refresh**: If a request returns a `401 Unauthorized` status, the central API client intercepts it, triggers `POST /auth/refresh`, updates the token, and retries the failed request.
4. **Logout**: Frontend invokes `POST /auth/logout` and clears token caches.

---

## 4. Real-time Streaming (SSE)
- Endpoint: `POST /agent/execute/stream`.
- Since browser `EventSource` lacks support for custom auth headers and POST request bodies, the frontend uses `fetch` with `ReadableStream` decoding chunks in real time.
- Incoming event logs stream safe states (`EXECUTION_STARTED`, `PLANNER_STARTED`, `TOOL_COMPLETED`, etc.) to update the workspace execution stage logs.

---

## 5. Security & Isolation Enforcement
- **No Client Trust**: Backend enforces security checks strictly in JWT context. Client-side user or workspace parameters are validated against authenticated profile structures.
- **Credentials Masking**: Backend scrubs credentials and API keys. The frontend never accesses raw AI credentials.
