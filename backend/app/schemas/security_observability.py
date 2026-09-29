import uuid
import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.core.security_events import SecurityEventType, SecuritySeverity

class SecurityEventItem(BaseModel):
    event_id: str
    event_type: SecurityEventType
    timestamp: datetime.datetime
    severity: SecuritySeverity
    actor_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    team_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    execution_id: Optional[str] = None
    source_component: str
    action: str
    outcome: str
    reason: Optional[str] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    security_metadata: Dict[str, Any] = Field(default_factory=dict)
    sanitized_details: Dict[str, Any] = Field(default_factory=dict)
    event_hash: Optional[str] = None
    previous_hash: Optional[str] = None

class SecurityEventListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    events: List[SecurityEventItem]

class SecurityAlertItem(BaseModel):
    alert_id: str
    rule_name: str
    title: str
    description: str
    severity: SecuritySeverity
    status: str = "ACTIVE" # ACTIVE, ACKNOWLEDGED, RESOLVED
    workspace_id: Optional[uuid.UUID] = None
    actor_id: Optional[uuid.UUID] = None
    correlation_id: Optional[str] = None
    execution_id: Optional[str] = None
    trigger_count: int = 1
    first_triggered_at: datetime.datetime
    last_triggered_at: datetime.datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SecurityAlertListResponse(BaseModel):
    total: int
    alerts: List[SecurityAlertItem]

class SecurityMetricsResponse(BaseModel):
    time_window: str
    total_events: int
    events_by_severity: Dict[str, int]
    events_by_category: Dict[str, int]
    authentication_metrics: Dict[str, int]
    authorization_metrics: Dict[str, int]
    ai_mcp_security_metrics: Dict[str, int]
    total_active_alerts: int
    alerts_by_severity: Dict[str, int]
    recent_suspicious_incidents: List[Dict[str, Any]] = Field(default_factory=list)

class IncidentEvidenceTimelineItem(BaseModel):
    timestamp: datetime.datetime
    component: str
    event_type: str
    identifier: str # event_id, execution_id, request_id, etc.
    summary: str
    details: Dict[str, Any] = Field(default_factory=dict)

class IncidentEvidenceResponse(BaseModel):
    query_param: str
    query_value: str
    workspace_id: Optional[uuid.UUID] = None
    actor_id: Optional[uuid.UUID] = None
    correlation_id: Optional[str] = None
    execution_id: Optional[str] = None
    request_id: Optional[str] = None
    total_records_found: int
    timeline: List[IncidentEvidenceTimelineItem] = Field(default_factory=list)

class AuditIntegrityResponse(BaseModel):
    is_valid: bool
    total_events_verified: int
    tampered_events_count: int
    broken_links_count: int
    tampered_event_ids: List[str] = Field(default_factory=list)
    latest_chain_hash: Optional[str] = None
    verification_timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

class RetentionPolicyResponse(BaseModel):
    retention_days_audit_logs: int
    retention_days_security_events: int
    retention_days_telemetry: int
    eligible_records_count: int
    oldest_record_timestamp: Optional[datetime.datetime] = None
    is_dry_run: bool = True
