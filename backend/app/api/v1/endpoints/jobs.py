import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.database.session import get_db
from app.api.dependencies import get_current_user, check_rate_limit
from app.models.user import User
from app.models.job import BackgroundJob, JobStatus
from app.schemas.job import (
    BackgroundJobCreate,
    BackgroundJobResponse,
    BackgroundJobListResponse,
    WorkerHealthResponse
)
from app.services.worker_service import WorkerService
from app.core.queue import QueueManager
from app.core.config import settings
from app.api.v1.endpoints.documents import resolve_workspace_id

router = APIRouter(prefix="/jobs", tags=["Background Jobs & Workers"])


@router.post("/", response_model=BackgroundJobResponse, status_code=status.HTTP_201_CREATED)
def create_background_job(
    payload: BackgroundJobCreate,
    workspace_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_rate_limit)
):
    """
    Enqueues a new background job with tenant isolation, deduplication, and priority scheduling.
    """
    ws_id = workspace_id or resolve_workspace_id(current_user, db)
    worker_svc = WorkerService(db)

    try:
        job = worker_svc.enqueue_job(
            workspace_id=ws_id,
            created_by=current_user.id,
            job_type=payload.job_type,
            payload=payload.payload,
            priority=payload.priority,
            scheduled_at=payload.scheduled_at,
            idempotency_key=payload.idempotency_key,
            correlation_id=payload.correlation_id,
            max_attempts=payload.max_attempts
        )
        return job
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.get("/", response_model=BackgroundJobListResponse)
def list_background_jobs(
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    job_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    workspace_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_rate_limit)
):
    """
    Lists background jobs within the user's current workspace.
    """
    ws_id = workspace_id or resolve_workspace_id(current_user, db)

    query = db.query(BackgroundJob).filter(
        and_(
            BackgroundJob.workspace_id == ws_id,
            BackgroundJob.deleted_at.is_(None)
        )
    )

    if status_filter:
        query = query.filter(BackgroundJob.status == status_filter)
    if job_type:
        query = query.filter(BackgroundJob.job_type == job_type)

    total = query.count()
    jobs = query.order_by(desc(BackgroundJob.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    return BackgroundJobListResponse(
        jobs=jobs,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/cluster/health", response_model=WorkerHealthResponse)
def get_worker_cluster_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_rate_limit)
):
    """
    Returns worker node registry, queue depths, and global concurrency limit.
    """
    queue_mgr = QueueManager()
    active_workers = queue_mgr.get_active_workers()
    queue_depths = queue_mgr.get_queue_depth()

    return WorkerHealthResponse(
        active_workers=active_workers,
        queue_depths=queue_depths,
        system_concurrency=settings.WORKER_CONCURRENCY
    )


@router.get("/{job_id}", response_model=BackgroundJobResponse)
def get_background_job(
    job_id: uuid.UUID,
    workspace_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_rate_limit)
):
    """
    Retrieves a single background job by ID with tenant boundary verification.
    """
    ws_id = workspace_id or resolve_workspace_id(current_user, db)

    job = db.query(BackgroundJob).filter(
        and_(
            BackgroundJob.id == job_id,
            BackgroundJob.workspace_id == ws_id,
            BackgroundJob.deleted_at.is_(None)
        )
    ).first()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Background job not found.")

    return job


@router.post("/{job_id}/cancel", response_model=BackgroundJobResponse)
def cancel_background_job(
    job_id: uuid.UUID,
    workspace_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(check_rate_limit)
):
    """
    Cancels a queued or running background job within tenant boundary.
    """
    ws_id = workspace_id or resolve_workspace_id(current_user, db)
    worker_svc = WorkerService(db)

    try:
        job = worker_svc.cancel_job(job_id=job_id, workspace_id=ws_id, user_id=current_user.id)
        return job
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
