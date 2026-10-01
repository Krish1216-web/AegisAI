# AegisAI Enterprise — Phase 11.7 Production-Like Staging Environment

**Document ID**: `89-Staging-Environment.md`  
**System**: AegisAI — Autonomous Multi-Agent System with MCP and Long-Term Memory  
**Target Environment**: Staging (Production-Mirror Topology)  
**Security Level**: Enterprise Restricted  
**Status**: `VERIFIED LOCALLY` / `IMPLEMENTED`

---

## 1. Executive Summary & Objective

Phase 11.7 establishes a dedicated, isolated, production-like Staging Environment for AegisAI. The staging environment accurately mirrors the production topology, container definitions, resource limits, security profiles, database migration mechanics, and worker architectures without sharing any production databases, Redis instances, cryptographic keys, object storage, or credentials.

The environment guarantees:
- **Topology Parity**: Full stack mirroring (Nginx SSL/TLS proxy, Frontend, Backend API, PostgreSQL 16, Redis 7, Background Worker, Distributed Scheduler).
- **Strict Isolation**: Separate database (`aegisai_staging`), dedicated Redis database, isolated storage (`storage/staging`), and isolated Docker internal network (`aegis-staging-internal-net`).
- **Fail-Fast Validation**: Dedicated `StagingConfig` rejecting SQLite, weak keys, default credentials, wildcard CORS/Hosts, and accidental production database connections.
- **Controlled State Management**: Safe staging reset utility guarded against non-staging execution, combined with an idempotent, deterministic data seeder creating multi-tenant organizations (Alpha/Beta), role hierarchies, workflows, documents, and MCP fixtures.
- **Automated Smoke Testing**: Comprehensive 12-subsystem automated staging smoke test suite integrated with CI/CD delivery pipelines.

---

## 2. Architecture & Topology Comparison

```
                         [ CLIENT / CI-CD RUNNER ]
                                     |
                                   HTTPS
                                     |
                         [ Staging Reverse Proxy ]
                            (Nginx / Port 443)
                                     |
                 ┌───────────────────┴───────────────────┐
                 |                                       |
       [ Staging Frontend ]                    [ Staging Backend API ]
      (Vite SPA / Port 3001)                  (FastAPI / Port 8001)
                                                         |
                           ┌─────────────────────────────┼─────────────────────────────┐
                           |                             |                             |
                [ Staging PostgreSQL 16 ]        [ Staging Redis 7 ]            [ Staging Storage ]
                 (aegisai_staging DB)             (Isolated Instance)            (storage/staging)
                           |                             |                             |
                 ┌─────────┴─────────┐         ┌─────────┴─────────┐                   |
                 |                   |         |                   |                   |
         [ Staging Worker ]   [ Staging Scheduler (Leader Lock) ] ─────────────────────┘
```

### Environment Isolation Matrix

| Attribute | Production | Staging | Development | Test |
| :--- | :--- | :--- | :--- | :--- |
| **ENVIRONMENT Profile** | `prod` (`ProductionConfig`) | `staging` (`StagingConfig`) | `dev` (`DevelopmentConfig`) | `test` (`TestConfig`) |
| **Database Name** | `aegisai_prod` | `aegisai_staging` | `aegisai_dev` | `aegisai_test` |
| **PostgreSQL Host Exposure** | Internal only (No host ports) | Internal only (No host ports) | `localhost:5432` | In-memory / Isolated |
| **Redis Host Exposure** | Internal only (No host ports) | Internal only (No host ports) | `localhost:6379` | Mock / Isolated |
| **Docker Network** | `aegis-prod-internal-net` (internal) | `aegis-staging-internal-net` (internal) | `aegis-dev-net` | Bridge |
| **Storage Directory** | `storage/prod` | `storage/staging` | `storage/dev` | `storage/test` |
| **HSTS & TLS** | Required / Enforced | Required / Enforced | Disabled | Disabled |
| **CORS Origins** | `https://app.aegisai.enterprise` | `https://staging.aegisai.enterprise` | `http://localhost:3000` | `*` (Mock) |
| **Container User** | Non-root `UID 10001` (`aegisuser`) | Non-root `UID 10001` (`aegisuser`) | Root / Dev user | Local runner |

---

## 3. Staging Configuration Profile (`StagingConfig`)

Located in [`backend/app/core/config.py`](file:///d:/CP/AegisAI/backend/app/core/config.py):

```python
class StagingConfig(BaseConfig):
    ENVIRONMENT: str = "staging"
    ENABLE_HSTS: bool = True
    POSTGRES_DB: str = "aegisai_staging"
    DOCUMENT_STORAGE_PATH: str = "storage/staging"
    LOG_LEVEL: str = "DEBUG"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    WORKER_CONCURRENCY: int = 4
    MAX_TENANT_CONCURRENCY: int = 2

    class Config:
        env_file = ".env.staging"
```

### Fail-Fast Configuration Invariants
[`validate_production_configuration`](file:///d:/CP/AegisAI/backend/app/core/config.py#L156-L211) enforces:
1. **Secret Key Entropy**: Minimum 32 characters; default placeholder strings rejected.
2. **Database Integrity**: Complete ban on SQLite; dedicated PostgreSQL database required.
3. **Password Security**: Default password `"postgres"` strictly rejected.
4. **Environment Cross-Contamination Guard**: If `ENVIRONMENT="staging"`, connecting to `aegisai_prod` throws a fatal validation error.
5. **Network Boundaries**: Wildcard origins (`"*"`) prohibited in `CORS_ORIGINS` and `ALLOWED_HOSTS`.
6. **Pool Limits**: Connection pool bounds bounded between 5 and 100 connections.

---

## 4. Staging Container Infrastructure (`docker-compose.staging.yml`)

Located in [`docker-compose.staging.yml`](file:///d:/CP/AegisAI/docker-compose.staging.yml) and [`docker/production/docker-compose.staging.yml`](file:///d:/CP/AegisAI/docker/production/docker-compose.staging.yml):

### Key Specifications:
- **Backend**: Multi-stage build (`Dockerfile.backend.prod`), non-root `UID 10001`, resource limits (`1.5 CPUs`, `1.5GB RAM`), health probe `/health/liveness`.
- **Worker**: Multi-stage build, executes `python -m app.worker`, non-root `UID 10001`, resource limits (`2.0 CPUs`, `2.0GB RAM`).
- **Scheduler**: Multi-stage build, executes `python -m app.scheduler`, single-leader Redis advisory lock, resource limits (`0.5 CPUs`, `512MB RAM`).
- **Frontend**: Multi-stage Nginx unprivileged build (`Dockerfile.frontend.prod`), non-root `UID 10001`, resource limits (`0.5 CPUs`, `512MB RAM`), health check `GET /healthz`.
- **Database (`db`)**: `postgres:16-alpine`, internal network only, persistent volume `aegis_postgres_staging_data`, `pg_isready` healthcheck.
- **Redis (`redis`)**: `redis:7-alpine`, internal network only, persistent volume `aegis_redis_staging_data`, `redis-cli ping` healthcheck.
- **Network**: `aegis-staging-internal-net` declared with `internal: true` to prevent external container egress/ingress bypassing proxy.

---

## 5. Safe Staging Database Reset & Seeding

### Safe Database Reset Utility
Located in [`backend/app/database/staging_reset.py`](file:///d:/CP/AegisAI/backend/app/database/staging_reset.py):
- **Guards**: Checks `ENVIRONMENT == "staging"`. Attempting execution in `prod`, `dev`, or `test` raises `StagingResetSafetyError`.
- **Confirmation Flag**: Requires explicit `force=True` parameter / `--force` CLI flag.
- **Concurrency**: Acquires PostgreSQL migration advisory lock (`AEGIS_MIGRATION_ADVISORY_LOCK_ID = 849204910294810293`) before resetting schema.
- **Execution Flow**: Drops all tables in `public` schema -> Executes linear Alembic upgrade to `head` (`019_background_jobs`) -> Invokes deterministic staging seeder.

### Deterministic Staging Data Seeder
Located in [`backend/app/database/staging_seed.py`](file:///d:/CP/AegisAI/backend/app/database/staging_seed.py):
- **Idempotency**: All operations check for pre-existing records by deterministic UUIDs and unique email/username indices.
- **Tenancy Fixtures**:
  - **Organization Alpha**: ID `11111111-1111-4111-a111-111111111111` -> **Workspace Alpha** (`33333333-3333-4333-a333-333333333333`).
  - **Organization Beta**: ID `22222222-2222-4222-a222-222222222222` -> **Workspace Beta** (`44444444-4444-4444-a444-444444444444`).
- **User Personas**:
  - `staging_superadmin@aegisai.enterprise` (Role: Super Admin)
  - `staging_admin@aegisai.enterprise` (Role: Admin, Workspace Alpha Owner)
  - `staging_member@aegisai.enterprise` (Role: User, Workspace Alpha Member)
  - `staging_viewer@aegisai.enterprise` (Role: Viewer, Workspace Alpha Viewer)
  - `staging_isolated@aegisai.enterprise` (Role: Admin, Workspace Beta Owner)
- **Subsystem Fixtures**: Seed documents with checksums, knowledge graph nodes/edges, workflow templates, team hierarchies, and mock MCP tools.

---

## 6. Staging Smoke Test Automation Suite

Located in [`backend/tests/staging/test_staging_smoke_suite.py`](file:///d:/CP/AegisAI/backend/tests/staging/test_staging_smoke_suite.py):

| Test ID | Subsystem | Verification Scope | Status |
| :--- | :--- | :--- | :--- |
| `01_AUTH` | Auth & Session | Registration, token issuance, session liveness | `VERIFIED LOCALLY` |
| `02_RBAC` | RBAC Controls | Protected endpoint authorization & rejection | `VERIFIED LOCALLY` |
| `03_TENANT` | Tenant Isolation | Cross-tenant workspace boundary separation (Alpha vs Beta) | `VERIFIED LOCALLY` |
| `04_AI` | AI Orchestration | Engine provider resolution and model routing | `VERIFIED LOCALLY` |
| `05_RAG` | RAG Engine | Document retrieval and staging storage isolation | `VERIFIED LOCALLY` |
| `06_GRAPH` | Knowledge Graph | Entity model schema, attributes, and tenant scoping | `VERIFIED LOCALLY` |
| `07_MCP` | MCP Integration | Tool discovery, capability registry, and secret redaction | `VERIFIED LOCALLY` |
| `08_WORKFLOW`| Workflow Engine | State machine transitions and DAG lifecycle | `VERIFIED LOCALLY` |
| `09_PLATFORM`| Execution Engine | Intelligence result structure and provenance items | `VERIFIED LOCALLY` |
| `10_OBSERV` | Observability | Correlation header propagation (`X-Correlation-ID`) & dependency health | `VERIFIED LOCALLY` |
| `11_SECURITY`| Security Headers | HSTS, CSP, `X-Content-Type-Options: nosniff`, `X-Frame-Options` | `VERIFIED LOCALLY` |
| `12_REALTIME`| Documents & Realtime | Storage integrity, checksum verification, and realtime boundaries | `VERIFIED LOCALLY` |

---

## 7. Operational Runbook

### Starting the Staging Environment
```bash
# 1. Prepare environment variables
cp .env.staging.example .env.staging

# 2. Build and start containers in isolated internal network
docker compose -f docker-compose.staging.yml up -d --build

# 3. Apply database migrations
docker compose -f docker-compose.staging.yml exec backend alembic upgrade head

# 4. Seed staging test fixtures
docker compose -f docker-compose.staging.yml exec backend python -m app.database.staging_seed
```

### Running Staging Smoke Verification
```bash
# Run automated smoke test suite against staging services
docker compose -f docker-compose.staging.yml exec backend pytest tests/staging/test_staging_smoke_suite.py -v
```

### Resetting Staging Database
```bash
# Safe reset with mandatory confirmation guard
docker compose -f docker-compose.staging.yml exec backend python -m app.database.staging_reset --force
```

---

## 8. Verification Matrix

| Requirement | Implementation Artifact | Verification Mode | Execution Result |
| :--- | :--- | :--- | :--- |
| Staging Profile Resolution | `StagingConfig` in `app.core.config` | Pytest Unit Test | `VERIFIED LOCALLY` (100% Pass) |
| Fail-Fast Config Validation | `validate_production_configuration` | Pytest Unit Test | `VERIFIED LOCALLY` (100% Pass) |
| Isolated Staging Network | `docker-compose.staging.yml` | Pytest YAML & Topology Test | `VERIFIED LOCALLY` (100% Pass) |
| Non-Exposed DB & Redis | Port bindings omitted in staging compose | Pytest Compose Inspector | `VERIFIED LOCALLY` (100% Pass) |
| Resource Limits Declared | `deploy.resources.limits` across all services | Pytest Compose Inspector | `VERIFIED LOCALLY` (100% Pass) |
| Staging Reset Guard | `reset_staging_database` (`staging_reset.py`) | Pytest Guard Safety Test | `VERIFIED LOCALLY` (100% Pass) |
| Idempotent Seeder | `seed_staging_environment` (`staging_seed.py`) | Pytest Seed Idempotency Test | `VERIFIED LOCALLY` (100% Pass) |
| Staging Smoke Suite | `test_staging_smoke_suite.py` (12 tests) | Pytest Smoke Suite | `VERIFIED LOCALLY` (12/12 Pass) |
| Dedicated Phase 11.7 Tests | `test_p11_7_staging_environment.py` (33 tests)| Pytest Unit Suite | `VERIFIED LOCALLY` (33/33 Pass) |
| Full Backend Regression | Full suite (`backend/tests/unit/`) | Pytest Regression Run | `VERIFIED LOCALLY` (853/853 Pass) |
| Frontend Test Suite | `frontend/src/__tests__/` (4 files) | Vitest Test Runner | `VERIFIED LOCALLY` (12/12 Pass) |
| Frontend Production Build | `npm run build` | Vite Production Builder | `VERIFIED LOCALLY` (2540 modules, 0 errors) |
| External Cloud Deployment | AWS ECS / Kubernetes / Baremetal Staging | Production Infrastructure Run | `REQUIRES STAGING INFRASTRUCTURE` |
