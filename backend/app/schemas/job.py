import uuid
import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict

from app.models.job import JobStatus, JobPriority, JobErrorCategory


class BackgroundJobCreate(BaseModel):
    job_type: str = Field(..., description="Type of job to execute")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Job parameters and input data")
    priority: int = Field(default=JobPriority.NORMAL.value, ge=1, le=100)
    scheduled_at: Optional[datetime.datetime] = None
    idempotency_key: Optional[str] = None
    correlation_id: Optional[str] = None
    max_attempts: int = Field(default=3, ge=1, le=10)


class BackgroundJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    created_by: uuid.UUID
    job_type: str
    status: JobStatus
    priority: int
    payload: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    idempotency_key: Optional[str] = None
    correlation_id: Optional[str] = None
    scheduled_at: datetime.datetime
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    heartbeat_at: Optional[datetime.datetime] = None
    attempts: int
    max_attempts: int
    next_retry_at: Optional[datetime.datetime] = None
    last_error: Optional[str] = None
    error_category: Optional[JobErrorCategory] = None
    worker_id: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class BackgroundJobListResponse(BaseModel):
    jobs: List[BackgroundJobResponse]
    total: int
    page: int
    page_size: int


class WorkerHealthResponse(BaseModel):
    active_workers: List[Dict[str, Any]]
    queue_depths: Dict[str, int]
    system_concurrency: int
