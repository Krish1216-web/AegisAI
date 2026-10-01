import uuid
import enum
import datetime
from sqlalchemy import String, Boolean, ForeignKey, Text, JSON, DateTime, Enum, Integer, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Dict, Any
from app.database.base_class import Base, AuditMixin


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    CLAIMED = "claimed"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    DEAD_LETTERED = "dead_lettered"
    RETRY_WAIT = "retry_wait"


class JobPriority(int, enum.Enum):
    LOW = 10
    NORMAL = 50
    HIGH = 80
    CRITICAL = 100


class JobErrorCategory(str, enum.Enum):
    TRANSIENT = "transient"
    PERMANENT_AUTH = "permanent_auth"
    PERMANENT_VALIDATION = "permanent_validation"
    PERMANENT_TENANT_ISOLATION = "permanent_tenant_isolation"
    PERMANENT_SECURITY = "permanent_security"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class BackgroundJob(Base, AuditMixin):
    """
    Persistent background job model with tenant isolation, atomic state tracking,
    retry limits, dead-lettering, and worker heartbeat coordination.
    """
    __tablename__ = "background_jobs"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    job_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=JobStatus.QUEUED,
        nullable=False,
        index=True
    )
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False, index=True)

    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    scheduled_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
        index=True
    )
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    next_retry_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_category: Mapped[Optional[JobErrorCategory]] = mapped_column(
        Enum(JobErrorCategory, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True
    )

    worker_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    lock_token: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    workspace = relationship("Workspace")
    creator = relationship("User")

    __table_args__ = (
        Index("ix_bgjobs_status_scheduled", "status", "scheduled_at"),
        Index("ix_bgjobs_ws_status", "workspace_id", "status"),
        Index("ix_bgjobs_ws_idempotency", "workspace_id", "idempotency_key"),
        Index("ix_bgjobs_stale_detection", "status", "heartbeat_at"),
    )
