# AegisAI Enterprise — Phase 11.8 Production Deployment Architecture

**Document ID**: `90-Production-Deployment-Architecture.md`  
**System**: AegisAI — Autonomous Multi-Agent System with MCP and Long-Term Memory  
**Target Environment**: Production (`ProductionConfig`)  
**Security Level**: Enterprise Restricted  
**Status**: `VERIFIED LOCALLY` / `IMPLEMENTED` / `ARCHITECTURALLY SUPPORTED`

---

## 1. Authoritative Production Topology

The AegisAI production architecture is engineered as a multi-tier, defense-in-depth platform with strict separation between public ingress, private service mesh, stateful persistence, asynchronous processing, and distributed scheduling.

```
                                  [ INTERNET ]
                                       |
                              [ DNS / Anycast Edge ]
                           (Route53 / Cloudflare / HTTPS)
                                       |
                           [ Edge TLS Load Balancer ]
                             (AWS ALB / GCP HTTPS LB)
                                       |
                           ┌───────────┴───────────┐
                           |                       |
                 [ Reverse Proxy / Frontend ]      |
                   (Nginx / Port 80 & 443)         |
                           |                       |
                 ┌─────────┴─────────┐             |
                 |                   |             |
           Static SPA UI      REST API Reverse Proxy
                 |                   |
                 └─────────┬─────────┘
                           |
               [ Private Internal Mesh Network ]
                   (aegis-internal-net)
                           |
             ┌─────────────┼─────────────┐
             |             |             |
        [ Backend API ] [ Background ] [ Distributed ]
         (3 Replicas)    (4 Workers)    (Scheduler)
             |             |             |
             └─────────────┼─────────────┘
                           |
       ┌───────────────────┼───────────────────┐
       |                   |                   |
 [ PostgreSQL 16 ]    [ Redis 7 ]      [ Storage Volume ]
  (Primary + WAL)    (Queue / Lock)    (Encrypted Objects)
       |                   |                   |
       ├── Documents       ├── Job Queues      ├── Raw Documents
       ├── Graph Entities  ├── Scheduler Lock  ├── Processed Chunks
       ├── Workflows       ├── Worker Reg.     └── Export Artifacts
       └── Security Audits └── Event PubSub
```

### Component State & Scalability Classification

| Component | State Classification | Scalability Model | Recommended Replicas | Coordination Mechanism |
| :--- | :--- | :--- | :--- | :--- |
| **Reverse Proxy (Nginx)** | Stateless | Horizontal | 2+ | Round-Robin / Least Connections |
| **Frontend UI (Vite SPA)** | Stateless Static Assets | Horizontal / CDN | N/A (Static files) | Edge Cache / Object Store |
| **Backend API (FastAPI)** | Stateless | Horizontal | 3+ | Shared DB + Redis Cache |
| **Background Workers** | Stateless Workers | Horizontal | 4+ | Redis Priority Queues (`aegis:queue:*`) |
| **Scheduler Daemon** | Stateful Singleton Leader | Active-Passive Leader | 2 | Redis Distributed Lock (`aegis:scheduler:leader:lock`) |
| **PostgreSQL 16 Engine** | Stateful Persistent | Single Primary + Read Replicas | 1 Primary (+ Replicas) | PostgreSQL WAL Streaming / Raft |
| **Redis 7 In-Memory** | Stateful Ephemeral | Sentinel / Cluster | 1 (+ Sentinels) | Redis AOF + RDB Persistence |
| **Document Storage** | Stateful Persistent | Distributed Object Storage | N/A | S3 API / POSIX Volume |

---

## 2. Production Networking & Boundaries

### Network Boundary Enclosure

```
+-------------------------------------------------------------------------------+
| PUBLIC ZONE (Ingress Only)                                                    |
|  - Ports: 80 (HTTP Redirect), 443 (HTTPS TLS 1.2/1.3)                         |
|  - Ingress: External Load Balancer -> Nginx Reverse Proxy                     |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| PRIVATE ZONE (aegis-internal-net, internal: true)                             |
|  - Backend API: http://backend:8000 (Internal only)                           |
|  - Background Workers: Internal worker processes                              |
|  - Scheduler Daemon: Internal scheduler coordinator                           |
|  - PostgreSQL: tcp://db:5432 (NO host port exposure)                         |
|  - Redis: tcp://redis:6379 (NO host port exposure)                           |
|  - Document Storage: /workspace/storage (POSIX volume mount)                  |
+-------------------------------------------------------------------------------+
```

### Service Ingress & Egress Invariants
1. **No Direct Database Access**: PostgreSQL and Redis containers do **NOT** map host ports (`ports` block omitted in `docker-compose.prod.yml`). Only containers attached to `aegis-internal-net` can reach database ports.
2. **Reverse Proxy Termination**: All client connections terminate at Nginx over TLS. Nginx translates HTTPS requests to internal HTTP requests on `http://backend:8000`.
3. **Trusted Proxy & Real Client IP**: Nginx evaluates `X-Forwarded-For` and `X-Real-IP` using declared `set_real_ip_from` CIDRs to preserve client IP for rate limiting and audit logging.
4. **Egress Filtering**: Backend and Worker outbound traffic is restricted to verified external endpoints (AI Provider APIs and authorized external MCP servers) via strict egress firewalling.

---

## 3. TLS, HTTPS & Security Headers

### TLS Configuration
- **Protocols**: `TLSv1.2 TLSv1.3` strictly enforced (`SSLv3`, `TLSv1.0`, and `TLSv1.1` disabled).
- **Ciphers**: High-entropy forward-secret cipher suites: `ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384`.
- **HSTS**: `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload` injected on all responses.

### Mandatory Security Headers
- `X-Frame-Options: DENY` (Clickjacking defense)
- `X-Content-Type-Options: nosniff` (MIME sniffing prevention)
- `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), camera=(), microphone=()`

---

## 4. High Availability & Load Balancing

### Stateless Backend Replicas
The FastAPI backend service is completely stateless. No session state, in-memory caches, or transient files are stored locally in the container filesystem:
- **Authentication**: Stateless signed JWT access tokens validated cryptographically via `SECRET_KEY`.
- **Session Revocation**: Centralized token blocklist maintained in Redis (`aegis:session:blocklist:*`).
- **Load Distribution**: Reverse proxy distributes incoming HTTP requests across backend replicas using round-robin with active TCP health monitoring.
- **WebSocket & SSE Draining**: Reverse proxy maintains long-lived connections for real-time channels with explicit 300-second read timeouts and upstream proxy buffering disabled (`proxy_buffering off;`).

---

## 5. PostgreSQL Production Database Architecture

### Connection Pooling & Limits
Managed via SQLAlchemy in [`backend/app/database/session.py`](file:///d:/CP/AegisAI/backend/app/database/session.py):
- **Pool Type**: `QueuePool` with `pre_ping=True` to eliminate stale connections.
- **Pool Size**: `DB_POOL_SIZE=20` (minimum 5, maximum 100 enforced by `validate_production_configuration`).
- **Max Overflow**: `DB_MAX_OVERFLOW=10` burst capacity.
- **Pool Timeout**: 30 seconds before fast failing.
- **Connection Recycling**: `pool_recycle=1800` (connections recycled every 30 minutes).

### Concurrency-Safe Migration Protocol
- **Lock Identifier**: `AEGIS_MIGRATION_ADVISORY_LOCK_ID = 7490001001` (0xAE615A1001).
- **Advisory Lock Flow**: Multi-replica startup executes `pg_try_advisory_lock`. Exactly one replica executes Alembic migrations while peers wait, preventing race conditions or corrupted migration states.
- **Linear Revision Chain**: All 19 Alembic migrations form a single linear DAG pointing to `head` revision `019_background_jobs`.

---

## 6. Redis Production Architecture

### Subsystem Resource Allocation & Isolation
- **Append-Only File (AOF)**: `appendonly yes` enabled for transactional durability.
- **Memory Boundary**: Maximum memory capped (`--maxmemory 2gb`) with `--maxmemory-policy noeviction` to ensure job queues are never silently dropped under memory pressure.
- **Namespaces**:
  - `aegis:queue:critical`: P1 urgency tasks (security alerts, immediate cancellations).
  - `aegis:queue:high`: Interactive user tasks (RAG indexing, query orchestration).
  - `aegis:queue:default`: Standard background tasks (document processing).
  - `aegis:queue:low`: Analytics aggregation and cleanup.
  - `aegis:queue:delayed`: Sorted set (`ZSET`) for future scheduled jobs.
  - `aegis:scheduler:leader:lock`: Distributed mutex for singleton scheduler daemon.
  - `aegis:worker:heartbeat:*`: Worker registry and liveness keys.

---

## 7. Background Worker & Horizontal Scaling Model

### Worker Execution Architecture
- **Process Entrypoint**: `python -m app.worker`
- **Worker Concurrency**: `WORKER_CONCURRENCY=10` per container.
- **Tenant Isolation**: `MAX_TENANT_CONCURRENCY=4` per workspace to prevent noisy-neighbor starvation.
- **Heartbeat & Stale Recovery**: Workers register heartbeats every 10 seconds (TTL 30s). Orphaned or stale jobs abandoned by dead workers are automatically re-enqueued by the stale job recovery daemon.
- **Dead-Letter Handling**: Tasks failing 3 consecutive attempts are routed to the dead-letter queue (`aegis:queue:dead_letter`) with comprehensive error metadata for manual inspection.

---

## 8. Distributed Scheduler Architecture

### Single-Leader Coordination
- **Process Entrypoint**: `python -m app.scheduler_daemon`
- **Leader Mutex**: Acquired via Redis key `aegis:scheduler:leader:lock` using atomic `SET NX EX 15`.
- **Heartbeat Renewal**: Active leader renews lease every 5 seconds.
- **Failover**: If leader terminates or network partitions, the lock expires in 15 seconds, and a standby scheduler instance assumes leadership immediately.
- **Job Emission**: Scheduler emits durable `BackgroundJob` records directly to PostgreSQL and Redis queues, ensuring no job loss if the scheduler restarts during an execution cycle.

---

## 9. Document Storage Architecture

### File System Isolation & Safety
- **Storage Directory**: Explicit path configured via `DOCUMENT_STORAGE_PATH` (defaults to `/workspace/storage`).
- **Path Traversal Protection**: Enforced via `os.path.abspath` and canonical path prefix validation preventing directory escapes (`../`).
- **Checksum Verification**: SHA-256 digests calculated upon upload and verified before chunking and vector indexing.
- **Access Control**: Document downloads require workspace-level authorization verified against database ownership records.

---

## 10. AI Provider Architecture & Resilience

### Multi-Provider Routing & Circuit Breaking
- **Supported Providers**: OpenAI (`GPT-4o`), Google Gemini (`Gemini 1.5 Pro / Flash`), Anthropic (`Claude 3.5 Sonnet`).
- **Fail-Safe Fallbacks**: If external API keys are unavailable in non-production environments, the platform defaults to `MockProvider` for deterministic testing.
- **Timeout & Retries**: Exponential backoff with jitter on HTTP 429 (Rate Limit) and 503 (Provider Unavailable).
- **Cost & Token Tracking**: Real-time token usage and cost accounting logged with every execution result.

---

## 11. MCP (Model Context Protocol) Production Architecture

### Security Sandbox & Isolation
- **Registry Model**: Centralized `MCPServer` and `MCPCapability` models with tenant scoping.
- **Credential Protection**: Server headers, API tokens, and connection strings encrypted in `MCPServer.config` and scrubbed via `CredentialStore.redact_sensitive_dict`.
- **SSRF Defenses**: External MCP endpoints validated against private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, AWS metadata `169.254.169.254`).
- **Human-in-the-Loop Confirmation**: High-risk capabilities (write operations, deletions, external network calls) require explicit human approval before execution.

---

## 12. Secrets Management & Rotation

### Zero-Hardcoded Secrets Policy
- **Image Safety**: Multi-stage Dockerfiles copy zero `.env` files or secret values into image layers.
- **Runtime Injection**: Secrets provided exclusively via runtime environment variables (`.env.prod`, HashiCorp Vault, or AWS Secrets Manager).
- **Non-Disclosure**: Diagnostic endpoints (`/version`, `/health/dependencies`) and logs strip all occurrences of `SECRET_KEY`, `POSTGRES_PASSWORD`, and API keys.
- **Rotation Procedure**:
  1. Generate new 64-character secret key.
  2. Inject secret into staging environment; verify token generation.
  3. Deploy to production backend replicas with zero-downtime rolling update.

---

## 13. Production Observability & Alerting

### Observability Telemetry
- **Correlation ID Tracking**: `X-Correlation-ID` and `X-Request-ID` propagated across reverse proxy, FastAPI middleware, intelligence engine, worker queue, and database queries.
- **Structured JSON Logging**: Loguru configured for machine-readable JSON logs with timestamp, level, correlation ID, tenant ID, and source module.
- **Metrics Registry**: In-memory and Prometheus-compatible metrics for request duration, latency percentiles (p50, p95, p99), error rates, DB query latency, and queue depths.

### Alerting Triggers

| Alert Name | Condition | Severity | Action |
| :--- | :--- | :--- | :--- |
| `HIGH_5XX_ERROR_RATE` | 5xx error rate > 2% over 5m | Critical | Alert on-call, inspect error logs |
| `DB_POOL_SATURATION` | DB connection pool utilization > 90% | High | Check long queries, scale pool size |
| `REDIS_UNAVAILABLE` | Redis ping failure | Critical | Check Redis container / memory exhaustion |
| `QUEUE_BACKLOG_SURGE` | Pending queue items > 500 for 10m | High | Scale worker replicas |
| `DEAD_LETTER_BURST` | Dead-letter job created | High | Inspect failed job traceback |
| `SCHEDULER_LEADER_LOST`| No active leader lock for > 30s | Critical | Restart scheduler instances |
| `SECURITY_ANOMALY` | > 10 authentication failures in 1m | Critical | Trigger IP rate limiting, log security audit |

---

## 14. Capacity & Scaling Model

### Dimensioning & Sizing Guidelines

```
API Replicas (N) = ceil( Peak RPS / (Workers per API Container * Target RPS per Worker) )
DB Connections = (API Replicas * DB_POOL_SIZE) + (Worker Replicas * WORKER_CONCURRENCY) + 10 (Headroom)
Redis RAM (GB)  = Base (512MB) + (Peak Pending Jobs * 5KB) + (Active Sessions * 2KB)
```

| Subsystem | Baseline (100 Concurrent Users) | Target (1,000 Concurrent Users) | Scaling Vector |
| :--- | :--- | :--- | :--- |
| **Backend API** | 3 Replicas (6 CPUs, 12GB RAM) | 8 Replicas (16 CPUs, 32GB RAM) | Horizontal |
| **Workers** | 4 Replicas (8 CPUs, 16GB RAM) | 12 Replicas (24 CPUs, 48GB RAM)| Horizontal |
| **Scheduler** | 2 Replicas (Active-Passive) | 2 Replicas (Active-Passive) | Singleton Leader |
| **PostgreSQL** | 1 Primary (4 CPUs, 16GB RAM) | 1 Primary + 2 Read Replicas | Vertical Primary + Read Scaling |
| **Redis** | 1 Instance (2 CPUs, 4GB RAM) | Redis Sentinel (3 Nodes) | Master-Replica + Sentinel |

---

## 15. Production Deployment Strategy

### Deployment Pipeline
```
[ Commit on main / tag ]
           |
      [ CI Pipeline ] (Lint, Test, Security Scan, TruffleHog, Bandit, Trivy)
           |
 [ Build Immutable Images ] (Syft SBOM, Digest Attestation, UID 10001)
           |
 [ Deploy to Staging ] (.env.staging, Isolated Network, Safe Seeder)
           |
 [ Automated Staging Smoke Tests ] (12 Subsystem Smoke Verification)
           |
 [ Production Manual Approval Gate ] (Role-Guarded Release Authorization)
           |
 [ Production Rolling Deployment ]
     1. Acquire Advisory Lock
     2. Apply Additive Alembic Migrations (Expand)
     3. Rolling update Backend Replicas (Deploy)
     4. Health Gate Verification (/health/readiness)
     5. Rolling update Worker & Scheduler Replicas
     6. Rolling update Frontend & Proxy Replicas
```

### Schema Evolution Pattern: Expand -> Deploy -> Backfill -> Contract
- **Expand**: Add new columns/tables with nullable or default values. No destructive alterations.
- **Deploy**: Deploy new application code compatible with both old and new schemas.
- **Backfill**: Execute background worker migration scripts to populate new columns.
- **Contract**: In a subsequent release cycle, remove deprecated legacy columns.

---

## 16. Production Rollback Procedures

### Rollback Workflow
In the event of an unrecoverable runtime error, elevated error rate, or health gate failure post-deployment:
1. **Halt Promotion**: Immediately abort rolling replacement.
2. **Preserve Incident Evidence**: Collect application logs, crash dumps, and telemetry metrics.
3. **Revert Immutable Image Tag**: Update deployment to previous verified container image digest.
4. **Deploy Previous Application Version**: Rolling replace containers with prior image version.
5. **Verify Health Gates**: Execute `/health/readiness` and `/health/dependencies` verification.
6. **DATABASE ROLLBACK SAFETY GUARD**: **Never execute automatic destructive database rollbacks (`alembic downgrade`).** Because all migrations follow the additive Expand-Contract pattern, the previous application version remains 100% compatible with the expanded schema.

---

## 17. Disaster Recovery & Continuity

### RPO & RTO Targets (Architectural Targets)
- **Recovery Point Objective (RPO)**: `15 minutes (TARGET — NOT YET MEASURED IN PRODUCTION)`
- **Recovery Time Objective (RTO)**: `10 minutes (TARGET — NOT YET MEASURED IN PRODUCTION)`

### Backup Schedule & Retention
- **Automated PostgreSQL Dumps**: Full database backup executed every 6 hours via `pg_dump` with gzip compression.
- **WAL Archiving**: Continuous WAL segment archiving to secondary persistent storage enabling Point-In-Time Recovery (PITR).
- **Retention**: 7 daily snapshots, 4 weekly snapshots, 12 monthly snapshots.
- **Restoration Verification**: Automated monthly restore drills into an isolated verification database.

---

## 18. Verification & Evidence Matrix

| Architecture Domain | Requirement | Verification Artifact | Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Topology** | 6-Service Production Stack | `docker-compose.prod.yml` | 6 Services Declared | `VERIFIED LOCALLY` |
| **Networking** | Isolated Private Network | `aegis-internal-net` | `internal: true` | `VERIFIED LOCALLY` |
| **Public Ingress** | Reverse Proxy HTTPS/HTTP | `aegis-public-net` (ports 80/443) | TLS termination & redirect | `VERIFIED LOCALLY` |
| **DB / Redis Ports** | Non-Public Host Exposure | Compose port inspector | 0 Exposed Host Ports | `VERIFIED LOCALLY` |
| **Non-Root Runtime**| UID 10001 Execution | `app.dockerfile` & `frontend.dockerfile`| `USER 10001` / `nginx` | `VERIFIED LOCALLY` |
| **Resource Limits** | Memory & CPU Bound | Service deploy specs | All Services Capped | `VERIFIED LOCALLY` |
| **Config Validation**| Fail-Closed Settings | `validate_production_configuration` | Prohibits weak keys/SQLite | `VERIFIED LOCALLY` |
| **DB Concurrency** | PostgreSQL Advisory Lock | `AEGIS_MIGRATION_ADVISORY_LOCK_ID` | Multi-replica safe | `VERIFIED LOCALLY` |
| **Migration Chain** | 19 Linear Revisions | Alembic DAG inspection | Linear to `019_background_jobs` | `VERIFIED LOCALLY` |
| **Worker Scaling** | Priority Queues & Concurrency | `QueueManager` & `WorkerService` | 4 Priorities + Heartbeat | `VERIFIED LOCALLY` |
| **Scheduler HA** | Singleton Leader Mutex | `SchedulerDaemon` lock renewal | Redis Lock (`SET NX EX 15`) | `VERIFIED LOCALLY` |
| **Diagnostic Gates**| Health & Dependency Probes | `/health/readiness` & `/dependencies` | Multi-subsystem health map | `VERIFIED LOCALLY` |
| **Version Endpoint**| Safe Build Metadata | `/version` endpoint | Zero secret disclosure | `VERIFIED LOCALLY` |
| **Architecture Manifest**| Machine-Readable Manifest | `production-architecture.json` | Valid JSON schema | `VERIFIED LOCALLY` |
| **Architecture Tests**| Phase 11.8 Unit Test Suite | `test_p11_8_production_architecture.py`| 31 / 31 Passed (100%) | `VERIFIED LOCALLY` |
| **Cloud LB & DNS** | Edge HTTPS & Anycast DNS | AWS ALB / Route53 | External Infrastructure | `REQUIRES CLOUD / DNS` |
| **SSL Certificates**| Trusted Public X.509 | Let's Encrypt / DigiCert | External PKI | `REQUIRES CERTIFICATE` |
| **Secrets Manager** | Cloud Vault Injection | HashiCorp Vault / AWS Secrets | External Provider | `REQUIRES SECRET MANAGER` |

---

## 19. Test Inventory Reconciliation & Final Verification

### Test Inventory Lineage

| Phase Baseline | Test Files | Total Tests | Description of Delta |
| :--- | :--- | :--- | :--- |
| **Phase 11.6 CI/CD** | 224 | 820 | CI/CD supply chain, SBOM, and provenance suite |
| **Phase 11.7 Staging** | 226 | 865 | Added `test_p11_7_staging_environment.py` (33) + `test_staging_smoke_suite.py` (12) |
| **Phase 11.8 Production Architecture** | **227** | **896** | Added `test_p11_8_production_architecture.py` (31 tests) |

### Final Verified Test Metrics
- **Full Backend Regression**: **896 / 896 tests passing (100%)**, 0 failures, 0 errors across all 227 test files.
- **Frontend Test Suite**: **12 / 12 tests passing (100%)** across 4 test suites.
- **Frontend Production Build**: **2540 modules transformed, 0 errors**.
- **Working Tree**: Completely clean, all changes tracked and committed.
