# Frontend Integration Testing

This document details test scenarios for validating frontend-backend integration, authentication routers, and SSE executions.

---

## 1. Authentication Tests
- **Register User**: Registers a new profile and verifies that a default organization and workspace are auto-provisioned.
- **Login Session**: Submits credentials, saves JWT token in `localStorage`, and recovers profile details with settings.
- **Access Verification**: Accessing protected paths triggers routing redirect loops back to `/login` if unauthenticated.
- **Refresh Interceptor**: Triggering api actions after access token expiry verifies that the client correctly rotates keys using HTTP-Only cookies.

---

## 2. Real-Time Streaming (SSE) Tests
- **Workspace Query**: Submitting a query prompt registers an active stream connection.
- **Event Sequence**: Verifies that the logs update in sequence on incoming SSE logs (`ORCHESTRATOR_STARTED` -> `PLANNER_STARTED` -> `TOOL_STARTED` -> `RESPONSE_GENERATING` -> `EXECUTION_COMPLETED`).
- **cancellation**: Clicking the Stop button terminates execution, publishes `EXECUTION_CANCELLED` and unlocks Redis locks.
- **confirmation**: Prompting high-risk tool runs shows the confirmation layout and resumes after validation token approval.

---

## 3. Security Tests
- **Isolation Boundaries**: Logged-in User A trying to query `GET /agent/executions/{id}` belonging to User B must result in a `403 Forbidden` response.
- **No Credentials**: Browser network inspect checks verify that no API keys or database connection strings are exposed in API JSON bodies.
