# 84. AegisAI — Production Database & Migration Infrastructure Specification

## 1. PostgreSQL Architecture
AegisAI utilizes PostgreSQL 16 (Alpine-based container or enterprise managed instance) as its primary relational state store. The system is designed around a clear separation of compute and state:

```
                      ┌────────────────────────────┐
                      │    Backend API Replicas    │
                      │  (FastAPI / ASGI Workers)  │
                      └──────────────┬─────────────┘
                                     │
                                     ▼
                      ┌────────────────────────────┐
                      │  SQLAlchemy Pool Manager   │
                      │ (Pre-ping, Recycle, Queue) │
                      └──────────────┬─────────────┘
                                     │
                                     ▼
                      ┌────────────────────────────┐
                      │   PostgreSQL 16 Engine     │
                      │ (Advisory Locks, Isolation)│
                      └──────────────┬─────────────┘
                                     │
                      ┌──────────────┴─────────────┐
                      ▼                            ▼
         ┌───────────────────────────┐ ┌───────────────────────────┐
         │     Persistent Volume     │ │    Backup & Retention     │
         │   (aegis_postgres_data)   │ │    (WAL / Daily Dumps)    │
         └───────────────────────────┘ └───────────────────────────┘
```

---

## 2. Connection Pooling Configuration
To prevent PostgreSQL connection starvation under concurrent traffic across multiple API replicas, background workers, and schedulers, SQLAlchemy is configured with bounded, recycled pools:

| Parameter | Default | Production Value | Rationale |
| :--- | :--- | :--- | :--- |
| `DB_POOL_SIZE` | `20` | `20` | Core persistent connection pool per process. |
| `DB_MAX_OVERFLOW` | `10` | `10` | Maximum burst connections beyond pool size during spikes. |
| `DB_POOL_TIMEOUT` | `30` | `30s` | Seconds to wait before raising TimeoutError when pool is exhausted. |
| `DB_POOL_RECYCLE` | `1800` | `1800s` (30 min) | Recycles connections to avoid dropped sockets through AWS/GCP NAT/ELB firewalls. |
| `DB_POOL_PRE_PING`| `True` | `True` | Issues `SELECT 1` ping before checkout to immediately discard stale connections. |
| `DB_CONNECT_TIMEOUT`| `10` | `10s` | Connect timeout preventing ASGI worker blockage during network partitioning. |

### Sizing Formula
$$\text{Total Connections} = (N_{\text{replicas}} \times N_{\text{workers}} \times (\text{PoolSize} + \text{MaxOverflow})) + N_{\text{background\_workers}} + N_{\text{scheduler}} + \text{AdminOverhead}$$
For a 3-replica cluster with 4 workers each:
$$\text{Total Connections} = (3 \times 4 \times (20 + 10)) + 10 + 2 + 5 = 377 \text{ connections}$$
PostgreSQL `max_connections` should be set to $\ge 450$.

---

## 3. Session Lifecycle & Transaction Safety
Database sessions are created per-request via the FastAPI dependency `get_db()`:

```python
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

- **Rollback Guarantee**: Unhandled exceptions immediately trigger `db.rollback()`, ensuring uncommitted or broken transactions never leak back to the connection pool.
- **Connection Return**: The `finally: db.close()` block unconditionally returns the connection to the SQLAlchemy pool.
- **Thread & Coroutine Safety**: Each request context executes in an independent session context.

---

## 4. Multi-Tenant Database Isolation
Tenant security is enforced at both the application logic layer and database model architecture:
1. **Mandatory `workspace_id`**: All multi-tenant tables (`teams`, `projects`, `comments`, `documents`, `document_chunks`, `knowledge_graph_nodes`, `memories`, `workflows`, `mcp_servers`) maintain a non-nullable or cascaded `workspace_id`.
2. **Indexed Tenant Lookups**: `workspace_id` columns are explicitly indexed (`index=True`) across all models, preventing cross-tenant table scans and accelerating tenant-filtered joins.
3. **Compound Key Constraints**: Unique constraints combine tenant boundaries (e.g. `uq_team_workspace_name` on `(workspace_id, name)`).

---

## 5. PostgreSQL Security Hardening
- **Network Isolation**: PostgreSQL runs on the private `aegis-internal` network. No database ports (`5432`) are published to the public internet or external host interfaces in production.
- **Credential Protection**:
  - Passwords and connection strings are injected via environment variables (`POSTGRES_PASSWORD`, `DATABASE_URL`).
  - Production validator rejects default passwords (`postgres`, `password`).
  - Passwords are encrypted in transit and redacted in all logs and health endpoints.
- **Dedicated User**: Applications connect via dedicated non-superuser credentials (`aegis_app`).

---

## 6. Alembic Architecture & History
The database schema history is managed via Alembic. The migration graph is strictly linear without unresolved branch points:

| Revision | Name | Description |
| :--- | :--- | :--- |
| `001_initial_migration` | Initial Migration | Core auth, user, organization, workspace, conversation, AI baseline |
| `002_add_ai_provider_tables` | Provider Tables | Request logging and provider health monitoring |
| `003_execution_persistence` | Execution Engine | Execution checkpoints, events, and tool telemetry |
| `004_agent_memory_persistence` | Memory | Agent memory and categorization |
| `005_documents` | Documents | Document metadata and storage tracking |
| `006_document_chunks` | Document Chunks | Chunk parsing, tokens, and chunk embeddings |
| `007_rag_queries` | RAG Queries | RAG query telemetry and retrieval stats |
| `008_knowledge_graph` | Knowledge Graph | Graph nodes, edges, entity relationships |
| `009_mcp_platform` | MCP Foundation | MCP server configuration and capabilities |
| `010_mcp_advanced_discovery` | MCP Discovery | Dynamic capability resolution |
| `011_workflow_engine_foundation` | Workflows | Nodes, edges, variables, workflow executions |
| `012_workflow_approval_governance` | Governance | Approval steps and role-based execution gating |
| `013_workflow_scheduling` | Scheduler | Cron scheduling and automated triggers |
| `014_team_collab_foundation` | Teams | Multi-user team entities and membership |
| `015_team_invitations` | Invitations | Workspace and team invitation tokens |
| `016_shared_projects_resources` | Projects | Shared workspace projects and resource binding |
| `017_comments_mentions` | Comments | Collaboration comments, replies, user mentions |
| `018_notifications_realtime` | Notifications | In-app notification feeds and preference matrices |
| `019_background_jobs` (HEAD) | Background Jobs | Asynchronous job queue, task execution, and dead-letter tracking |

---

## 7. Migration Workflow & Locking Architecture
To eliminate race conditions when deploying multiple backend replicas:

1. **Advisory Locking**: Migration execution uses PostgreSQL advisory locking (`pg_try_advisory_lock(7490001001)`).
2. **Deterministic Locking Sequence**:
   - Migration job initiates lock checkout.
   - If held by another replica, the runner retries with bounded exponential/linear backoff up to `lock_timeout` (default 30s).
   - Once acquired, `alembic.command.upgrade(config, "head")` executes.
   - The lock is unconditionally released in a `finally:` block.

---

## 8. Low-Downtime Migration Strategy (Expand/Contract)
For zero-downtime rolling upgrades in production:

1. **Expand Phase**: Add new columns (nullable or with default values), create new tables, and add indexes concurrently.
2. **Deploy Phase**: Roll out new backend application replicas capable of writing to both old and new schema fields.
3. **Data Backfill Phase**: Run offline asynchronous data backfill jobs if historical transformations are required.
4. **Contract Phase**: Deploy subsequent release deprecating old columns and safely drop unused legacy structures.

---

## 9. pgvector & Semantic Search
- `DocumentChunk` and `Memory` models integrate with vector embeddings (dimension `1536` for text-embedding-3-small).
- In PostgreSQL environments supporting `pgvector`, native vector columns enable hybrid lexical and semantic similarity indexing.
- For lightweight or external vector deployments, Qdrant acts as the dedicated ANN search backend while PostgreSQL retains relational metadata and chunk content.

---

## 10. Knowledge Graph Persistence
- `KnowledgeGraphNode`: Persistent graph entities with tenant isolation (`workspace_id`, `entity_type`, `name`, `properties`).
- `KnowledgeGraphEdge`: Persistent relationships with indexed source and target nodes (`source_node_id`, `target_node_id`, `relation_type`, `weight`).
- Traversal queries are bounded strictly to `workspace_id = :ws_id` preventing horizontal privilege escalation across graph graphs.

---

## 11. Cryptographic Audit & Security Persistence
- `AuditLog` and `SecurityEvent` tables capture high-fidelity operational events.
- Audit records include cryptographic hash chain linkages (`data_hash`, `previous_hash`, `record_hash`) ensuring tamper evidence.
- Read operations on audit tables are restricted to administrative scopes with immutable append-only insert semantics.

---

## 12. Backup Strategy
- **Daily Full Dumps**: Automated `pg_dump` executed during off-peak windows with AES-256 encryption.
- **Continuous Archiving**: WAL (Write-Ahead Logging) archiving to cloud object storage (S3/GCS bucket with Object Lock / WORM policy).
- **Retention**: 30-day point-in-time recovery (PITR), 365-day monthly archival snapshots.
- *Note*: Backup automation requires deployment-specific cloud storage infrastructure.

---

## 13. Restore Verification Procedure
1. Provision isolated staging database cluster.
2. Download and decrypt target backup snapshot.
3. Execute `pg_restore --clean --if-exists -d aegisai_restore backup.dump`.
4. Validate schema revision matches current Alembic head (`018_notifications_realtime`).
5. Execute synthetic smoke test suite against restored instance.

---

## 14. Health Probes & Readiness Isolation
- `GET /health/liveness`: Verifies ASGI web worker event loop is alive. Does NOT query the database to prevent transient DB stalls from causing cascading container restarts.
- `GET /health/readiness`: Queries `SELECT 1` on PostgreSQL and active ping on Redis. Returns `200 OK` when healthy and `503 Service Unavailable` on database disconnection without leaking internal connection credentials or tracebacks.

---

## 15. Operational Checklist
- [x] Connection pool limits properly tuned (`DB_POOL_SIZE=20`, `DB_MAX_OVERFLOW=10`).
- [x] Pool pre-ping enabled (`DB_POOL_PRE_PING=True`).
- [x] Non-root database execution and private internal Docker networking.
- [x] Linear Alembic migration chain verified up to `018_notifications_realtime`.
- [x] Multi-tenant indexed foreign keys confirmed on all domain models.
- [x] PostgreSQL advisory lock migration manager operational (`app.database.migration_manager`).
