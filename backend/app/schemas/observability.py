import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class RequestMetricsResponse(BaseModel):
    uptime_seconds: float = 0.0
    total_requests: int = 0
    throughput_rps: float = 0.0
    error_rate_percentage: float = 0.0
    status_code_distribution: Dict[str, int] = Field(default_factory=dict)
    error_categories: Dict[str, int] = Field(default_factory=dict)
    latency_ms: Dict[str, float] = Field(default_factory=dict)
    routes: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class DatabaseMetricsResponse(BaseModel):
    checkouts_total: int = 0
    rollbacks_total: int = 0
    connection_failures: int = 0
    pool_exhaustions: int = 0
    query_latency_ms: Dict[str, float] = Field(default_factory=dict)


class RedisMetricsResponse(BaseModel):
    operations_total: int = 0
    operation_errors: int = 0
    lock_contentions: int = 0


class WorkerMetricsResponse(BaseModel):
    jobs_queued: int = 0
    jobs_started: int = 0
    jobs_succeeded: int = 0
    jobs_failed: int = 0
    jobs_retried: int = 0
    jobs_dead_lettered: int = 0
    jobs_cancelled: int = 0
    jobs_stale_recovered: int = 0


class SchedulerMetricsResponse(BaseModel):
    cycles_total: int = 0
    schedules_triggered: int = 0
    duplicate_suppressions: int = 0


class InfrastructureMetricsResponse(BaseModel):
    database: DatabaseMetricsResponse = Field(default_factory=DatabaseMetricsResponse)
    redis: RedisMetricsResponse = Field(default_factory=RedisMetricsResponse)
    worker: WorkerMetricsResponse = Field(default_factory=WorkerMetricsResponse)
    scheduler: SchedulerMetricsResponse = Field(default_factory=SchedulerMetricsResponse)


class DomainMetricsResponse(BaseModel):
    agent: Dict[str, Any] = Field(default_factory=dict)
    rag: Dict[str, Any] = Field(default_factory=dict)
    graph: Dict[str, Any] = Field(default_factory=dict)
    mcp: Dict[str, Any] = Field(default_factory=dict)
    workflow: Dict[str, Any] = Field(default_factory=dict)


class OperationalAlertResponse(BaseModel):
    alert_id: str
    fingerprint: str
    rule_name: str
    severity: str  # "CRITICAL", "WARNING", "INFO"
    status: str    # "TRIGGERED", "ACKNOWLEDGED", "RESOLVED"
    title: str
    description: str
    metric_name: str
    current_value: float = 0.0
    threshold_value: float = 0.0
    triggered_at: datetime.datetime
    acknowledged_at: Optional[datetime.datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime.datetime] = None
    resolved_by: Optional[str] = None
    workspace_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OperationalAlertListResponse(BaseModel):
    total: int = 0
    alerts: List[OperationalAlertResponse] = Field(default_factory=list)


class ObservabilityOverviewResponse(BaseModel):
    status: str = "healthy"
    total_requests: int = 0
    error_rate_percentage: float = 0.0
    latency_p95_ms: float = 0.0
    active_alerts: int = 0
    critical_alerts: int = 0
    jobs_queued: int = 0
    jobs_dead_lettered: int = 0


class IncidentTimelineEvent(BaseModel):
    timestamp: datetime.datetime
    source: str  # "alert", "worker", "audit", "platform"
    event_type: str
    severity: str
    summary: str
    details: Dict[str, Any] = Field(default_factory=dict)


class IncidentTimelineResponse(BaseModel):
    query_id: str
    total_events: int = 0
    events: List[IncidentTimelineEvent] = Field(default_factory=list)
