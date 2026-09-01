# AegisAI Platform Production Hardening Guide (Phase 8.9)

## 1. Operational Security & Tenant Isolation
The AegisAI Platform enforces a zero-trust multi-tenant architecture across all capability adapters, agent reasoning loops, graph knowledge nodes, MCP servers, and background execution services.

### Core Hardening Tenets:
1. **Mandatory Tenant Scoping**: Every request context (`PlatformContext`) carries a verified `workspace_id` derived from authenticated JWT sessions. No caller can override this workspace boundary.
2. **Context Spoofing Immunity**: Even if malicious request payloads contain forged `workspace_id`, `user_id`, `role`, or `trust_level` fields, the platform rejects or ignores them in favor of the cryptographic session context.
3. **Deterministic State Machine**: Capability executions progress through an immutable 6-stage lifecycle (`REQUESTED -> PLANNED -> EXECUTING -> VERIFYING -> COMPLETED / FAILED / CANCELLED / DENIED`) preventing orphan or invalid state transitions.
4. **Secret Scrubbing & Redaction**: All structured inputs, payloads, error logs, and telemetry events pass through recursive redaction rules (`CredentialStore.redact_sensitive_dict`) ensuring zero credentials or private keys leak into logs or observability timelines.

---

## 2. Resilience, Bounded Execution & Concurrency Safety

### Execution Limits:
- **Maximum Execution Timeout**: Bounded at 300 seconds (configurable via `PLATFORM_MAX_TIMEOUT_SECONDS`).
- **Maximum Intelligence Plan Depth**: Hard limit of 6 levels.
- **Maximum Intelligence Steps**: Hard limit of 12 steps per query.
- **Cycle Prevention**: Directed Acyclic Graph (DAG) cycle detection with DFS coloring runs before any execution plan commences.

### Concurrency & Idempotency:
- **Tenant Concurrency Throttling**: Configurable max concurrent capability runs per workspace.
- **Idempotency Keys**: Requests providing `idempotency_key` are deduplicated and cached against the workspace scope, guaranteeing safe retries without side-effects.
- **Asynchronous Event Dispatcher Isolation**: Subscriber exceptions are caught, logged, and isolated from main execution workflows, preventing event crashes from failing user operations.

---

## 3. Provenance & Trust Hierarchy

Evidence items from disparate subsystems are tagged with immutable trust levels:
- `TRUSTED_INTERNAL`: Native platform synthesized intelligence.
- `VERIFIED_RAG`: Citations grounded in verified vector embeddings and documents.
- `VERIFIED_GRAPH`: Entity relations resolved through the internal Knowledge Graph.
- `VERIFIED_MEMORY`: Recalled facts from the managed episodic memory subsystem.
- `UNTRUSTED_MCP`: External MCP tool results requiring strict schema validation and security boundary checks.
- `UNTRUSTED_EXTERNAL`: Open internet research and web data.

Trust level escalation is blocked across the pipeline; external MCP tools cannot elevate their provenance status to internal trusted levels.
