# AegisAI Enterprise — Phase 11.4: Production Workers & Scheduling

## 1. Architectural Overview

Phase 11.4 establishes a robust, horizontally-scalable, and secure background execution and scheduling layer for AegisAI. The architecture combines database-backed state persistence (`BackgroundJob`) with Redis-backed distributed coordination, priority queues, delayed execution, worker heartbeats, and leader-elected cron scheduling.

```
                  +--------------------------------------------------+
                  |         AegisAI Web API / User Context           |
                  +-------------------------+------------------------+
                                            |
                      (Enqueue Job with Idempotency & Redaction)
                                            v
                  +--------------------------------------------------+
                  |           PostgreSQL `background_jobs`           |
                  |     (QUEUED, CLAIMED, RUNNING, SUCCEEDED, etc.)  |
                  +-------------------------+------------------------+
                                            |
                                (Redis Queue / Delayed ZSet)
                                            v
+---------------------------------------------------------------------------------------+
|                                    Redis Message Bus                                   |
|   - Priority Queues (critical / high / default / low)                                 |
|   - Delayed Jobs Set (`aegis:queue:delayed`, scored by epoch timestamp)               |
|   - Distributed Leader Lock (`aegis:scheduler:leader:lock`, TTL 15s)                  |
|   - Worker Heartbeat Registry (`aegis:worker:heartbeat:*`)                            |
+---------------------------------------------------------------------------------------+
                |                                                     |
                v                                                     v
+-------------------------------+                     +-------------------------------+
|     WorkerDaemon (Worker 1)   |                     |    SchedulerDaemon (Leader)   |
|  - Atomic DB/Redis Claim      |                     |  - Polls due WorkflowSchedules|
|  - Concurrency Bounds         |                     |  - Sweeps Delayed Queue       |
|  - Tenant-Isolated Context    |                     |  - Recovers Stale Worker Jobs |
|  - Exponential Backoff Jitter |                     |  - Enqueues background tasks  |
|  - Heartbeat Coordinator      |                     +-------------------------------+
|  - Graceful Shutdown (SIGTERM)|
+-------------------------------+
```

---

## 2. Persistent Job Data Model (`BackgroundJob`)

Located in [`backend/app/models/job.py`](file:///d:/CP/AegisAI/backend/app/models/job.py) and registered in database metadata through migration `019_background_jobs`.

### State Lifecycle:
- `QUEUED`: Enqueued, awaiting worker pickup.
- `CLAIMED`: Atomically locked by a worker node (`lock_token`, `worker_id`).
- `RUNNING`: Actively executing within security context and heartbeat updates.
- `SUCCEEDED`: Finished successfully, output stored in sanitized `result`.
- `RETRY_WAIT`: Transient error occurred; scheduled for retry after exponential backoff.
- `DEAD_LETTERED`: Exceeded `max_attempts` or failed with permanent unrecoverable security/auth error.
- `CANCEL_REQUESTED`: User requested cancellation while job was executing.
- `CANCELLED`: Cancelled before execution started.

---

## 3. Atomic Claiming & Tenant Fairness

1. **Atomic Claiming**:
   - Workers query ready jobs sorted by `priority DESC, scheduled_at ASC, created_at ASC`.
   - Atomic status transition with `lock_token` and `worker_id` prevents duplicate execution across horizontal replicas.
2. **Tenant Concurrency Limits (`MAX_TENANT_CONCURRENCY`)**:
   - Prevents a single tenant from starving the worker cluster.
   - If an organization or workspace already has active jobs $\ge \text{MAX\_TENANT\_CONCURRENCY}$, candidate jobs from that tenant are skipped in favor of other tenants.

---

## 4. Retries, Exponential Backoff & Dead-Letter Classification

The `WorkerService` categorizes failures into:
- **Transient Failures** (`JobErrorCategory.TRANSIENT`, `TIMEOUT`, `UNKNOWN`): Network hiccups, Redis connection errors, rate limits.
  - Calculated delay: $\text{delay} = \min(\text{max\_backoff}, \text{base} \times 2^{\text{attempt}-1}) + \text{uniform}(0.1, 1.0)$.
  - Status becomes `RETRY_WAIT`, `next_retry_at = now + delay`.
- **Permanent Failures** (`JobErrorCategory.PERMANENT_AUTH`, `PERMANENT_TENANT_ISOLATION`, `PERMANENT_VALIDATION`, `PERMANENT_SECURITY`):
  - Immediately transitions to `DEAD_LETTERED`. No retry cycles wasted.
  - Generates tamper-evident audit records in `SecurityObservabilityService`.

---

## 5. Distributed Leader Election & Workflow Scheduling

- `SchedulerDaemon` uses distributed locking (`aegis:scheduler:leader:lock`) in Redis with automatic token renewal and safe Lua script release.
- Only the elected leader evaluates due `WorkflowSchedule` instances, converts cron expressions in UTC, and asynchronously enqueues them via `WorkerService.enqueue_job`.
- Leader also moves expired delayed items from Redis sorted sets into execution priority queues.

---

## 6. Stale Job Recovery & Graceful Shutdown

- **Worker Heartbeats**: Every active job periodically updates `heartbeat_at`.
- **Stale Job Recovery**: The leader periodically searches for jobs in `CLAIMED` or `RUNNING` where `heartbeat_at < now - WORKER_STALE_TIMEOUT_SECONDS`. Stale jobs are automatically recovered into `RETRY_WAIT` (or dead-lettered if retry limit exceeded).
- **Graceful Shutdown**: The worker hooks `SIGTERM` and `SIGINT`, halts new job claiming, drains active threads for up to `WORKER_SHUTDOWN_TIMEOUT_SECONDS`, and safely releases distributed resources.

---

## 7. Verification & Regression Metrics

- **Dedicated Phase 11.4 Unit Tests**: 30 / 30 passed (`tests/unit/test_p11_4_workers_scheduling.py`).
- **Total Backend Unit Regression**: 755 / 755 passed across 222 test suites.
- **Frontend Vitest Tests**: 12 / 12 passed.
- **Frontend Production Build**: 2540 modules transformed, 0 errors.
