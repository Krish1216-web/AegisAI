# Security Policy — AegisAI

AegisAI is engineered from the ground up with a defense-in-depth security architecture designed for enterprise deployments. This policy outlines our security practices, vulnerability disclosure process, and boundary guarantees.

---

## 🛡️ Supported Versions

Only the active development branch and official release tags receive active security patches.

| Version | Supported | Security Maintenance Status |
| :--- | :--- | :--- |
| `v1.0.0-rc (Phase 11/12)` | Yes | Active Development & Hardening |
| `< 1.0.0` | No | Deprecated / Milestone Previews |

---

## 🔒 Reporting a Vulnerability

If you discover a security vulnerability in AegisAI, **please do NOT create a public GitHub issue**.

Instead, report vulnerabilities privately by emailing the security maintainers:
- **Email**: `security@aegisai.local` (or through GitHub Private Security Advisories)
- **Encryption**: If sensitive proof-of-concept material is included, please request a PGP key prior to transmission.

### When submitting a report, please include:
1. Type of vulnerability (e.g., SSRF, Auth Bypass, Tenant Isolation Leak, Prompt Injection).
2. Affected components (e.g., `app/services/mcp/`, `app/core/auth.py`, `frontend/src/api/`).
3. Step-by-step reproduction instructions or proof-of-concept script.
4. Impact assessment on multi-tenant isolation or execution integrity.

We commit to acknowledging reports within **48 hours** and providing patch timelines within **7 business days**.

---

## 🏛️ Security Architecture Guarantees

AegisAI enforces the following foundational security controls:

### 1. Multi-Tenant Isolation
- All database entities, vector chunks, memory records, and workflow definitions are strictly bound to a `workspace_id`.
- Tenant context is extracted from verified JWT claims on every request. Direct tenant overrides via URL parameters are rejected.

### 2. Dual-Tier RBAC & Effective Permissions
- System-level and Team-level roles:
  - System: `super_admin`, `admin`, `user`.
  - Team: `owner`, `maintainer`, `editor`, `viewer`.
- Evaluated hierarchically before any mutations, workflow executions, or administrative reads.

### 3. MCP Sandboxing & SSRF Mitigation
- Outbound requests to MCP servers undergo strict domain allowlisting and RFC 1918 private IP blocking to prevent Server-Side Request Forgery (SSRF).
- Subprocess executions via STDIO transport enforce process timeouts, CPU constraints, and isolated environment variables.

### 4. Cryptographic Audit Ledger
- All administrative actions, policy modifications, and high-risk executions are recorded with SHA-256 hashed chain links (`previous_hash` + `current_record_hash`) to guarantee tamper-evidence.

### 5. Sensitive Data Redaction
- Platform execution engines, agent provenance logs, and workflow histories pass through an automated regex and entropy redaction filter to scrub JWT tokens, API keys, and connection strings before serialization.
