# Phase 6.9: MCP Production Hardening & Operational Resilience

## Overview
This document details the hardening controls, operational guardrails, fault-tolerance mechanisms, and production testing verifications implemented for the Model Context Protocol (MCP) subsystem across AegisAI.

---

## 1. Tenant Isolation & IDOR Protection
- **Direct Workspace Scoping**: All database queries for `MCPServer`, `MCPCapability`, `ToolExecution`, and `Execution` join or filter by `workspace_id`.
- **404 Masking**: Unauthorized cross-tenant queries return `404 NOT FOUND` instead of `403 FORBIDDEN` to eliminate tenant discovery and timing attacks.
- **Audit Logging**: Cross-tenant attempts trigger `TENANT_MISMATCH` audit log entries.

---

## 2. Cryptographic Single-Use Confirmation Gates
- **Token Generation**: HMAC-SHA256 hash incorporating `user_id`, `workspace_id`, `tool_id`, sorted `arguments_hash`, and a random UUID nonce.
- **Single-Use Consumption**: Tokens are deleted from the registry immediately upon evaluation. Replays, argument modifications, and expired tokens are rejected.
- **Time Bounding**: Default token validity is 300 seconds.

---

## 3. Concurrency & Execution Locks
- **Redis Distributed Locking**: Critical discovery and execution paths acquire distributed Redis locks (`aegis:lock:mcp:exec:{workspace_id}:{tool_id}`).
- **Local Fallback Locks**: In the absence of Redis, thread-safe in-memory sets prevent duplicate simultaneous executions of idempotent actions.

---

## 4. Connection Resilience, Retries & Timeouts
- **Exponential Backoff & Jitter**: Failed connections retry up to 3 times with exponential backoff and randomized jitter to prevent thundering herds.
- **Non-Retriable Failures**: Authentication errors (`MCPAuthError`), validation errors (`MCPValidationError`), and client cancellations are non-retriable.
- **Strict Timeouts**: Default execution timeout is 15s; maximum allowed timeout is capped at 60s.

---

## 5. Input Validation, SSRF & Command Injection Defense
- **URL & URI Sanitization**: `MCPValidator.validate_server_url` strips dangerous shell characters (`$`, `;`, `|`, `&`, `` ` ``).
- **SSRF Defense**: `MCPValidator.validate_resource_uri` prohibits loopback (`127.0.0.1`, `::1`), private ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), and AWS metadata (`169.254.169.254`).
- **Filesystem Traversal**: Prohibits `file://` URIs and relative traversal components (`..`).
- **Payload Boundaries**:
  - Tool arguments $\le 32\text{ KB}$
  - Prompt arguments $\le 32\text{ KB}$
  - Metadata payloads $\le 64\text{ KB}$
  - JSON Schema nesting depth $\le 6$
  - Resource content preview truncated at $1\text{ MB}$

---

## 6. Prompt Injection Defense & Data Boundaries
- **Untrusted Stamping**: External MCP data is stamped with `UNTRUSTED_MCP`.
- **System Instruction Isolation**: MCP resources and prompt templates are treated as data, never replacing or overriding system instructions.
- **Critic Verification**: `CriticAgent` validates that all citations correspond to existing server and capability records in the active workspace.

---

## 7. Credential Protection & Sensitive Data Redaction
- **Storage Encryption**: Credentials in `auth_config` are masked on read.
- **Deep Redaction**: `CredentialStore.redact_sensitive_dict` recursively removes keys matching tokens, passwords, secrets, API keys, and bearer headers before returning execution traces, logs, or audit records.

---

## 8. Frontend Security & Robustness
- **Zero Raw HTML Execution**: React components render MCP outputs as structured text without `dangerouslySetInnerHTML`.
- **Client-Side Secrets**: No tokens or passwords stored in `localStorage` (only non-sensitive pinned UI preferences).
- **HTTP Error UX**: Standardized handling of status codes 403, 404, 409, 428, 429, and 5xx.
