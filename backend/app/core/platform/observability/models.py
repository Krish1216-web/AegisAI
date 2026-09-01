import uuid
import datetime
import enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class TimeWindow(str, enum.Enum):
    ONE_HOUR = "1h"
    TWENTY_FOUR_HOURS = "24h"
    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"

    @classmethod
    def to_timedelta(cls, window_str: str) -> datetime.timedelta:
        norm = (window_str or "24h").lower().strip()
        if norm == "1h":
            return datetime.timedelta(hours=1)
        elif norm == "24h":
            return datetime.timedelta(hours=24)
        elif norm == "7d":
            return datetime.timedelta(days=7)
        elif norm == "30d":
            return datetime.timedelta(days=30)
        else:
            raise ValueError(f"Unsupported time window '{window_str}'. Valid: 1h, 24h, 7d, 30d")

class CapabilityHealth(str, enum.Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"

class BottleneckClassification(str, enum.Enum):
    SLOW_EXECUTION = "SLOW_EXECUTION"
    HIGH_FAILURE = "HIGH_FAILURE"
    HIGH_WAIT = "HIGH_WAIT"
    HIGH_VOLUME = "HIGH_VOLUME"
    NORMAL = "NORMAL"

class AlertSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"

class AlertStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"

# --- Models ---

class TimeSeriesPoint(BaseModel):
    timestamp: str
    total: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    denied: int = 0

class PlatformOverviewMetrics(BaseModel):
    time_window: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    cancelled_executions: int = 0
    denied_executions: int = 0
    waiting_executions: int = 0
    success_rate: float = 0.0
    failure_rate: float = 0.0
    cancellation_rate: float = 0.0
    avg_duration_ms: float = 0.0
    median_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    p99_duration_ms: float = 0.0
    active_executions: int = 0
    executions_per_capability: Dict[str, int] = Field(default_factory=dict)
    executions_over_time: List[TimeSeriesPoint] = Field(default_factory=list)

class CapabilityPerformanceMetric(BaseModel):
    capability_id: str
    capability_type: str
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    denied_count: int = 0
    cancellation_count: int = 0
    success_rate: float = 0.0
    median_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    error_rate: float = 0.0
    health: CapabilityHealth = CapabilityHealth.UNKNOWN

class CapabilityAnalyticsResponse(BaseModel):
    time_window: str
    total_capabilities: int
    items: List[CapabilityPerformanceMetric] = Field(default_factory=list)

class LifecycleMetrics(BaseModel):
    time_window: str
    stage_durations_ms: Dict[str, float] = Field(default_factory=dict)
    status_distribution: Dict[str, int] = Field(default_factory=dict)
    status_percentages: Dict[str, float] = Field(default_factory=dict)

class BottleneckMetric(BaseModel):
    capability_id: str
    stage: str
    avg_duration_ms: float
    p95_duration_ms: float
    failure_rate: float
    classification: BottleneckClassification
    recommendation: str

class BottleneckAnalyticsResponse(BaseModel):
    time_window: str
    bottlenecks: List[BottleneckMetric] = Field(default_factory=list)

class IntelligenceAnalytics(BaseModel):
    time_window: str
    total_executions: int = 0
    requirement_distribution: Dict[str, int] = Field(default_factory=dict)
    execution_mode_distribution: Dict[str, int] = Field(default_factory=dict)
    decision_distribution: Dict[str, int] = Field(default_factory=dict)
    avg_confidence: float = 0.0
    high_confidence_count: int = 0
    medium_confidence_count: int = 0
    low_confidence_count: int = 0
    insufficient_confidence_count: int = 0
    adaptive_attempt_distribution: Dict[int, int] = Field(default_factory=dict)
    fallback_count: int = 0
    retrieve_more_count: int = 0
    contradiction_count: int = 0

class ProvenanceAnalytics(BaseModel):
    time_window: str
    total_evidence_items: int = 0
    avg_evidence_per_execution: float = 0.0
    source_distribution: Dict[str, int] = Field(default_factory=dict)
    trust_distribution: Dict[str, int] = Field(default_factory=dict)
    citation_frequency: Dict[str, int] = Field(default_factory=dict)
    verified_vs_untrusted_ratio: float = 0.0

class FailureCategoryItem(BaseModel):
    category: str
    count: int
    percentage: float

class FailureItem(BaseModel):
    error_type: str
    category: str
    capability_id: str
    stage: str
    normalized_message: str
    occurrences: int
    latest_occurrence: datetime.datetime

class FailureAnalytics(BaseModel):
    time_window: str
    total_failures: int = 0
    failures_by_category: List[FailureCategoryItem] = Field(default_factory=list)
    failures_by_capability: Dict[str, int] = Field(default_factory=dict)
    failures_by_stage: Dict[str, int] = Field(default_factory=dict)
    recent_failures: List[FailureItem] = Field(default_factory=list)

class PlatformAlert(BaseModel):
    alert_id: str
    severity: AlertSeverity
    alert_type: str
    title: str
    description: str
    capability_id: Optional[str] = None
    detected_at: datetime.datetime
    status: AlertStatus = AlertStatus.ACTIVE

class AlertAnalyticsResponse(BaseModel):
    time_window: str
    total_alerts: int
    alerts: List[PlatformAlert] = Field(default_factory=list)

class ExecutionTimelineEvent(BaseModel):
    timestamp: datetime.datetime
    event_type: str
    lifecycle_state: str
    capability_id: str
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ExecutionTimeline(BaseModel):
    execution_id: str
    correlation_id: str
    capability_id: str
    status: str
    started_at: datetime.datetime
    completed_at: Optional[datetime.datetime] = None
    total_duration_ms: float = 0.0
    events: List[ExecutionTimelineEvent] = Field(default_factory=list)
