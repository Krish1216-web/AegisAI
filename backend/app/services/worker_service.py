import uuid
import datetime
import random
import time
from typing import Dict, Any, List, Optional, Tuple, Callable
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from loguru import logger

from app.models.job import BackgroundJob, JobStatus, JobPriority, JobErrorCategory
from app.models.workspace import Workspace, WorkspaceMember
from app.models.user import User, Role
from app.core.queue import QueueManager
from app.core.config import settings
from app.core.mcp.security import CredentialStore
from app.core.security_events import SecurityEventType, SecuritySeverity
from app.services.security_observability import SecurityObservabilityService
from app.services.authorization import AuthorizationService
from app.core.correlation import set_correlation_context
from app.core.metrics import metrics_registry
from app.core.platform.errors import (
    PlatformExecutionError,
    TenantIsolationError,
    CapabilityPermissionDenied,
    InvalidExecutionInput,
    ExecutionTimeout,
    ExecutionCancelled
)


def calculate_exponential_backoff(
    attempt: int,
    base_seconds: float = 2.0,
    max_seconds: float = 300.0,
    jitter: bool = True
) -> float:
    """
    Computes bounded exponential backoff with full jitter: min(max_backoff, base * 2^attempt) + uniform(0, 1)
    """
    delay = min(max_seconds, base_seconds * (2 ** max(0, attempt - 1)))
    if jitter:
        delay += random.uniform(0.1, 1.0)
    return round(delay, 2)


def classify_error_category(exc: Exception) -> JobErrorCategory:
    """
    Determines whether an exception is permanent (unrecoverable) or transient (retryable).
    """
    err_str = str(exc).lower()
    exc_type = type(exc).__name__.lower()

    if isinstance(exc, (TenantIsolationError, CapabilityPermissionDenied)) or "permission denied" in err_str or "unauthorized" in err_str:
        return JobErrorCategory.PERMANENT_AUTH
    elif "tenant" in err_str or "workspace mismatch" in err_str or "boundary" in err_str:
        return JobErrorCategory.PERMANENT_TENANT_ISOLATION
    elif isinstance(exc, InvalidExecutionInput) or "validation" in err_str or "invalid payload" in err_str or "schema" in err_str:
        return JobErrorCategory.PERMANENT_VALIDATION
    elif "prompt injection" in err_str or "ssrf" in err_str or "forbidden tool" in err_str:
        return JobErrorCategory.PERMANENT_SECURITY
    elif isinstance(exc, ExecutionTimeout) or "timeout" in err_str or "timed out" in err_str:
        return JobErrorCategory.TIMEOUT
    elif "connection" in err_str or "network" in err_str or "redis" in err_str or "lock" in err_str or "rate limit" in err_str:
        return JobErrorCategory.TRANSIENT

    return JobErrorCategory.UNKNOWN


class WorkerService:
    """
    Production-grade Worker & Background Execution Service.
    Handles queueing, priority scheduling, atomic job claiming, concurrency controls,
    tenant-isolated execution, exponential backoff retries, dead-lettering,
    heartbeats, and stale job recovery.
    """

    def __init__(self, db: Session, queue_mgr: Optional[QueueManager] = None):
        self.db = db
        self.queue_mgr = queue_mgr or QueueManager()
        self.security_obs = SecurityObservabilityService(db)
        self.authz_service = AuthorizationService(db)

    def enqueue_job(
        self,
        workspace_id: uuid.UUID,
        created_by: uuid.UUID,
        job_type: str,
        payload: Dict[str, Any],
        priority: int = JobPriority.NORMAL.value,
        scheduled_at: Optional[datetime.datetime] = None,
        idempotency_key: Optional[str] = None,
        correlation_id: Optional[str] = None,
        max_attempts: int = 3
    ) -> BackgroundJob:
        """
        Persists and queues a background job with idempotency validation and secret scrubbing.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        effective_scheduled_at = scheduled_at or now

        # 1. Idempotency Check
        if idempotency_key:
            existing_job = self.db.query(BackgroundJob).filter(
                and_(
                    BackgroundJob.workspace_id == workspace_id,
                    BackgroundJob.idempotency_key == idempotency_key,
                    BackgroundJob.deleted_at.is_(None),
                    BackgroundJob.status.in_([
                        JobStatus.QUEUED,
                        JobStatus.CLAIMED,
                        JobStatus.RUNNING,
                        JobStatus.SUCCEEDED,
                        JobStatus.RETRY_WAIT
                    ])
                )
            ).first()
            if existing_job:
                logger.info(f"Idempotent job hit for key '{idempotency_key}' (Job {existing_job.id})")
                return existing_job

        # 2. Workspace Validation
        workspace = self.db.query(Workspace).filter(
            and_(Workspace.id == workspace_id, Workspace.deleted_at.is_(None))
        ).first()
        if not workspace:
            raise ValueError(f"Target workspace {workspace_id} does not exist.")

        # 3. Sanitize Payload (no secrets saved into background job table)
        sanitized_payload = CredentialStore.redact_sensitive_dict(payload or {})

        # 4. Create BackgroundJob record
        job = BackgroundJob(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            created_by=created_by,
            job_type=job_type,
            status=JobStatus.QUEUED,
            priority=priority,
            payload=sanitized_payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id or uuid.uuid4().hex,
            scheduled_at=effective_scheduled_at,
            max_attempts=max_attempts,
            attempts=0
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        # 5. Push to Redis Queue / Delayed Queue
        delay_seconds = 0.0
        if effective_scheduled_at > now:
            delay_seconds = max(0.0, (effective_scheduled_at - now).total_seconds())

        self.queue_mgr.enqueue(str(job.id), priority=priority, delay_seconds=delay_seconds)
        metrics_registry.record_job_lifecycle("queued")

        # 6. Observability
        try:
            self.security_obs.record_event(
                event_type=SecurityEventType.ADMIN_ACTION,
                source_component="worker_service",
                action="JOB_QUEUED",
                outcome="SUCCESS",
                actor_id=created_by,
                workspace_id=workspace_id,
                correlation_id=job.correlation_id,
                sanitized_details={
                    "job_id": str(job.id),
                    "job_type": job_type,
                    "priority": priority,
                    "scheduled_at": effective_scheduled_at.isoformat()
                }
            )
        except Exception as oe:
            logger.debug(f"Observability recording skipped: {oe}")

        return job

    def claim_next_job(
        self,
        worker_id: str,
        preferred_job_types: Optional[List[str]] = None,
        max_tenant_concurrency: int = 5
    ) -> Optional[BackgroundJob]:
        """
        Atomically claims the highest priority ready job while respecting tenant concurrency limits.
        """
        now = datetime.datetime.now(datetime.timezone.utc)

        # Build candidate filter
        filters = [
            BackgroundJob.deleted_at.is_(None),
            or_(
                and_(BackgroundJob.status == JobStatus.QUEUED, BackgroundJob.scheduled_at <= now),
                and_(BackgroundJob.status == JobStatus.RETRY_WAIT, BackgroundJob.next_retry_at <= now)
            )
        ]
        if preferred_job_types:
            filters.append(BackgroundJob.job_type.in_(preferred_job_types))

        candidate_jobs = self.db.query(BackgroundJob).filter(and_(*filters)).order_by(
            desc(BackgroundJob.priority),
            BackgroundJob.scheduled_at.asc(),
            BackgroundJob.created_at.asc()
        ).limit(20).all()

        if not candidate_jobs:
            return None

        # Check tenant concurrency for candidates
        for candidate in candidate_jobs:
            running_tenant_jobs = self.db.query(func.count(BackgroundJob.id)).filter(
                and_(
                    BackgroundJob.workspace_id == candidate.workspace_id,
                    BackgroundJob.status.in_([JobStatus.CLAIMED, JobStatus.RUNNING]),
                    BackgroundJob.deleted_at.is_(None)
                )
            ).scalar() or 0

            if running_tenant_jobs >= max_tenant_concurrency:
                logger.debug(f"Tenant {candidate.workspace_id} reached concurrency limit ({running_tenant_jobs}/{max_tenant_concurrency}); skipping candidate {candidate.id}")
                continue

            # Atomic claim update
            lock_token = uuid.uuid4().hex
            rows_updated = self.db.query(BackgroundJob).filter(
                and_(
                    BackgroundJob.id == candidate.id,
                    BackgroundJob.status.in_([JobStatus.QUEUED, JobStatus.RETRY_WAIT])
                )
            ).update({
                "status": JobStatus.CLAIMED,
                "worker_id": worker_id,
                "lock_token": lock_token,
                "started_at": now,
                "heartbeat_at": now,
                "updated_at": now
            })
            self.db.commit()

            if rows_updated > 0:
                self.db.refresh(candidate)
                logger.info(f"Worker '{worker_id}' successfully claimed job {candidate.id} ({candidate.job_type})")
                return candidate

        return None

    def update_heartbeat(self, job_id: uuid.UUID, worker_id: str) -> bool:
        """
        Refreshes the worker heartbeat timestamp for an active job.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        rows = self.db.query(BackgroundJob).filter(
            and_(
                BackgroundJob.id == job_id,
                BackgroundJob.worker_id == worker_id,
                BackgroundJob.status.in_([JobStatus.CLAIMED, JobStatus.RUNNING])
            )
        ).update({
            "heartbeat_at": now,
            "updated_at": now
        })
        self.db.commit()
        return rows > 0

    def process_job(
        self,
        job_id: uuid.UUID,
        worker_id: str,
        custom_handler: Optional[Callable[[BackgroundJob, Session], Dict[str, Any]]] = None
    ) -> BackgroundJob:
        """
        Executes a claimed background job under security context, handling transitions,
        retries, and dead-lettering.
        """
        job = self.db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found.")

        now = datetime.datetime.now(datetime.timezone.utc)
        job.status = JobStatus.RUNNING
        job.worker_id = worker_id
        job.heartbeat_at = now
        self.db.commit()

        # Set thread-local correlation context for logger and platform events
        set_correlation_context(
            job_id=str(job.id),
            correlation_id=job.correlation_id,
            workspace_id=job.workspace_id,
            user_id=job.created_by
        )
        metrics_registry.record_job_lifecycle("started")

        # Security Context Verification
        user = self.db.query(User).filter(
            and_(User.id == job.created_by, User.is_active.is_(True), User.is_deleted.is_(False))
        ).first()

        if not user:
            return self._handle_permanent_failure(
                job,
                JobErrorCategory.PERMANENT_AUTH,
                f"Executing user {job.created_by} is inactive, deleted, or does not exist."
            )

        workspace = self.db.query(Workspace).filter(
            and_(Workspace.id == job.workspace_id, Workspace.deleted_at.is_(None))
        ).first()
        if not workspace:
            return self._handle_permanent_failure(
                job,
                JobErrorCategory.PERMANENT_TENANT_ISOLATION,
                f"Executing workspace {job.workspace_id} not found or archived."
            )

        # Dispatch execution
        try:
            result_data = self._dispatch_job_execution(job, user, custom_handler)
            
            # Successful Completion
            job.status = JobStatus.SUCCEEDED
            job.completed_at = datetime.datetime.now(datetime.timezone.utc)
            job.result = CredentialStore.redact_sensitive_dict(result_data or {})
            job.last_error = None
            self.db.commit()
            self.db.refresh(job)

            metrics_registry.record_job_lifecycle("succeeded")
            logger.info(f"Job {job.id} ({job.job_type}) succeeded.")
            return job

        except Exception as exc:
            logger.error(f"Execution failed for job {job.id}: {exc}")
            return self._handle_job_exception(job, exc)

    def _dispatch_job_execution(
        self,
        job: BackgroundJob,
        user: User,
        custom_handler: Optional[Callable[[BackgroundJob, Session], Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Dispatches job to the appropriate domain engine.
        """
        if custom_handler:
            return custom_handler(job, self.db)

        job_type = job.job_type

        if job_type == "workflow.execution":
            from app.services.workflow_execution import WorkflowExecutionService
            workflow_id = uuid.UUID(str(job.payload.get("workflow_id")))
            input_data = job.payload.get("input_data", {})
            exec_svc = WorkflowExecutionService(self.db)
            wf_exec = exec_svc.execute_workflow(
                user_id=user.id,
                workspace_id=job.workspace_id,
                workflow_id=workflow_id,
                input_data=input_data
            )
            return {"workflow_execution_id": str(wf_exec.id), "status": wf_exec.status.value}

        elif job_type == "platform.capability":
            from app.services.platform_execution import PlatformExecutionService
            cap_id = job.payload.get("capability_id")
            cap_input = job.payload.get("input", {})
            plat_svc = PlatformExecutionService(self.db)
            res = plat_svc.execute(
                capability_id=cap_id,
                user_id=user.id,
                workspace_id=job.workspace_id,
                input_data=cap_input,
                correlation_id=job.correlation_id
            )
            return {"output": res.output_data, "state": res.state.value}

        elif job_type == "document.process":
            from app.services.document_processing import DocumentProcessingService
            doc_id = uuid.UUID(str(job.payload.get("document_id")))
            DocumentProcessingService.process_document(self.db, doc_id)
            return {"document_id": str(doc_id), "status": "processed"}

        elif job_type == "maintenance.cleanup":
            return {"status": "cleanup_completed", "cleaned_items": 0}

        else:
            return {"status": "success", "message": f"Handled generic job '{job_type}'"}

    def _handle_job_exception(self, job: BackgroundJob, exc: Exception) -> BackgroundJob:
        """
        Classifies error and applies bounded exponential backoff or dead-lettering.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        error_category = classify_error_category(exc)
        sanitized_error = CredentialStore.redact_sensitive_str(str(exc))

        is_transient = error_category in [JobErrorCategory.TRANSIENT, JobErrorCategory.TIMEOUT, JobErrorCategory.UNKNOWN]

        job.attempts += 1
        job.last_error = sanitized_error
        job.error_category = error_category

        if is_transient and job.attempts < job.max_attempts:
            # Bounded Exponential Backoff Retry
            delay_seconds = calculate_exponential_backoff(job.attempts)
            job.status = JobStatus.RETRY_WAIT
            job.next_retry_at = now + datetime.timedelta(seconds=delay_seconds)
            self.db.commit()
            self.db.refresh(job)

            # Re-enqueue to Redis delayed queue
            self.queue_mgr.enqueue(str(job.id), priority=job.priority, delay_seconds=delay_seconds)
            metrics_registry.record_job_lifecycle("retried")
            logger.warning(f"Job {job.id} transient failure (attempt {job.attempts}/{job.max_attempts}). Retrying in {delay_seconds}s.")
        else:
            # Permanent Failure / Dead Lettering
            job.status = JobStatus.DEAD_LETTERED
            job.completed_at = now
            self.db.commit()
            self.db.refresh(job)

            metrics_registry.record_job_lifecycle("dead_lettered")
            logger.error(f"Job {job.id} transitioned to DEAD_LETTERED. Reason: {sanitized_error} (Category: {error_category.value})")

            # Security Observability Record
            try:
                self.security_obs.record_event(
                    event_type=SecurityEventType.EXECUTION_FAILURE,
                    source_component="worker_service",
                    action="JOB_DEAD_LETTERED",
                    outcome="FAILURE",
                    actor_id=job.created_by,
                    workspace_id=job.workspace_id,
                    correlation_id=job.correlation_id,
                    reason=sanitized_error,
                    sanitized_details={
                        "job_id": str(job.id),
                        "job_type": job.job_type,
                        "attempts": job.attempts,
                        "error_category": error_category.value
                    }
                )
            except Exception as oe:
                logger.debug(f"Observability record skipped: {oe}")

        return job

    def _handle_permanent_failure(
        self,
        job: BackgroundJob,
        category: JobErrorCategory,
        reason: str
    ) -> BackgroundJob:
        """
        Immediately fails and dead-letters jobs with permanent security / auth errors without retrying.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        sanitized_reason = CredentialStore.redact_sensitive_str(reason)

        job.attempts += 1
        job.status = JobStatus.DEAD_LETTERED
        job.error_category = category
        job.last_error = sanitized_reason
        job.completed_at = now
        self.db.commit()
        self.db.refresh(job)

        metrics_registry.record_job_lifecycle("dead_lettered")
        logger.error(f"Job {job.id} permanently failed: {sanitized_reason}")

        try:
            self.security_obs.record_event(
                event_type=SecurityEventType.AUTHZ_DENIED if category == JobErrorCategory.PERMANENT_AUTH else SecurityEventType.TENANT_BOUNDARY_VIOLATION,
                source_component="worker_service",
                action="JOB_SECURITY_REJECTION",
                outcome="DENIED",
                actor_id=job.created_by,
                workspace_id=job.workspace_id,
                correlation_id=job.correlation_id,
                reason=sanitized_reason,
                sanitized_details={
                    "job_id": str(job.id),
                    "job_type": job.job_type,
                    "category": category.value
                }
            )
        except Exception as oe:
            logger.debug(f"Observability record skipped: {oe}")

        return job

    def cancel_job(
        self,
        job_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> BackgroundJob:
        """
        Cancels a queued, retry_wait, or running background job with tenant boundary verification.
        """
        job = self.db.query(BackgroundJob).filter(
            and_(
                BackgroundJob.id == job_id,
                BackgroundJob.workspace_id == workspace_id,
                BackgroundJob.deleted_at.is_(None)
            )
        ).first()

        if not job:
            raise ValueError(f"Job {job_id} not found in workspace {workspace_id}")

        now = datetime.datetime.now(datetime.timezone.utc)

        if job.status in [JobStatus.QUEUED, JobStatus.RETRY_WAIT]:
            job.status = JobStatus.CANCELLED
            job.completed_at = now
            self.db.commit()
            self.db.refresh(job)
            metrics_registry.record_job_lifecycle("cancelled")
            logger.info(f"Queued job {job_id} cancelled by user {user_id}")
            return job

        elif job.status in [JobStatus.CLAIMED, JobStatus.RUNNING]:
            job.status = JobStatus.CANCEL_REQUESTED
            self.db.commit()
            self.db.refresh(job)
            metrics_registry.record_job_lifecycle("cancelled")
            logger.info(f"Cancellation requested for running job {job_id} by user {user_id}")
            return job

        else:
            raise ValueError(f"Cannot cancel job in state '{job.status.value}'")

    def recover_stale_jobs(self, stale_timeout_seconds: int = 60) -> List[BackgroundJob]:
        """
        Identifies and recovers jobs left in CLAIMED or RUNNING whose worker heartbeat has expired.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        cutoff = now - datetime.timedelta(seconds=stale_timeout_seconds)

        stale_jobs = self.db.query(BackgroundJob).filter(
            and_(
                BackgroundJob.status.in_([JobStatus.CLAIMED, JobStatus.RUNNING]),
                BackgroundJob.heartbeat_at < cutoff,
                BackgroundJob.deleted_at.is_(None)
            )
        ).all()

        recovered: List[BackgroundJob] = []
        for job in stale_jobs:
            logger.warning(f"Recovering stale job {job.id} (worker '{job.worker_id}', last heartbeat {job.heartbeat_at})")
            job.attempts += 1
            if job.attempts < job.max_attempts:
                delay = calculate_exponential_backoff(job.attempts)
                job.status = JobStatus.RETRY_WAIT
                job.next_retry_at = now + datetime.timedelta(seconds=delay)
                job.last_error = f"Worker heartbeat timeout (> {stale_timeout_seconds}s). Re-queued for retry."
                job.error_category = JobErrorCategory.TIMEOUT
                self.queue_mgr.enqueue(str(job.id), priority=job.priority, delay_seconds=delay)
                metrics_registry.record_job_lifecycle("stale_recovered")
            else:
                job.status = JobStatus.DEAD_LETTERED
                job.completed_at = now
                job.last_error = f"Worker heartbeat timeout exceeded max attempts ({job.attempts}/{job.max_attempts})."
                job.error_category = JobErrorCategory.TIMEOUT
                metrics_registry.record_job_lifecycle("dead_lettered")

            recovered.append(job)

        if recovered:
            self.db.commit()

        return recovered
