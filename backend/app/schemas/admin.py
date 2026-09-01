import uuid
import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class AdminOverviewResponse(BaseModel):
    total_users: int = 0
    active_users: int = 0
    suspended_users: int = 0
    total_workspaces: int = 0
    active_workspaces: int = 0
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    cancelled_executions: int = 0
    active_capabilities: int = 0
    active_mcp_servers: int = 0
    active_workflows: int = 0
    avg_latency_ms: float = 0.0
    success_rate: float = 100.0
    system_status: str = "ONLINE"
    alerts_count: int = 0
    security_alerts_count: int = 0
    time_window: str = "24h"

class AdminUserWorkspaceInfo(BaseModel):
    workspace_id: uuid.UUID
    workspace_name: str
    role: str

class AdminUserListItem(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    role: str
    is_active: bool
    is_verified: bool
    is_deleted: bool
    created_at: datetime.datetime
    last_activity: Optional[datetime.datetime] = None
    workspaces_count: int = 0
    workspaces: List[AdminUserWorkspaceInfo] = Field(default_factory=list)

class AdminUserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    users: List[AdminUserListItem]

class AdminUserDetailResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    role: str
    is_active: bool
    is_verified: bool
    is_deleted: bool
    avatar_url: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime.datetime
    workspaces: List[AdminUserWorkspaceInfo] = Field(default_factory=list)
    recent_audit_logs: List[Dict[str, Any]] = Field(default_factory=list)

class AdminUserStatusUpdateRequest(BaseModel):
    is_active: bool
    reason: Optional[str] = None

class AdminUserRoleUpdateRequest(BaseModel):
    role_name: str

class AdminWorkspaceListItem(BaseModel):
    id: uuid.UUID
    name: str
    organization_id: uuid.UUID
    created_at: datetime.datetime
    members_count: int = 0
    documents_count: int = 0
    workflows_count: int = 0
    mcp_servers_count: int = 0
    executions_count: int = 0
    status: str = "active"

class AdminWorkspaceListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    workspaces: List[AdminWorkspaceListItem]

class AdminRoleInfo(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    users_count: int = 0

class AdminRolePermissionResponse(BaseModel):
    roles: List[AdminRoleInfo]
    permission_matrix: List[Dict[str, Any]]
    capability_permissions: List[Dict[str, Any]]

class SubsystemHealth(BaseModel):
    name: str
    status: str  # ONLINE, DEGRADED, UNAVAILABLE
    latency_ms: float = 0.0
    details: Dict[str, Any] = Field(default_factory=dict)

class AdminSystemHealthResponse(BaseModel):
    overall_status: str
    timestamp: float
    environment: str
    subsystems: List[SubsystemHealth]

class AdminExecutionListItem(BaseModel):
    execution_id: str
    capability_id: str
    capability_name: Optional[str] = None
    status: str
    workspace_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    duration_ms: float = 0.0
    started_at: datetime.datetime
    completed_at: Optional[datetime.datetime] = None
    correlation_id: str
    errors_count: int = 0

class AdminExecutionListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    executions: List[AdminExecutionListItem]

class AdminAuditLogItem(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    username: Optional[str] = None
    action: str
    ip_address: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime.datetime

class AdminAuditLogListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    logs: List[AdminAuditLogItem]

class AdminSecurityPostureResponse(BaseModel):
    tenant_isolation_enforced: bool = True
    rbac_posture: str = "STRICT"
    confirmation_gate_active: bool = True
    ssrf_defense_active: bool = True
    secret_redaction_active: bool = True
    total_security_denials: int = 0
    recent_denials: List[Dict[str, Any]] = Field(default_factory=list)
    recent_alerts: List[Dict[str, Any]] = Field(default_factory=list)

class AdminActivityFeedItem(BaseModel):
    event_id: str
    event_type: str
    source_component: str
    workspace_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    timestamp: datetime.datetime
    summary: str
    payload: Dict[str, Any] = Field(default_factory=dict)

class AdminActivityFeedResponse(BaseModel):
    total: int
    events: List[AdminActivityFeedItem]

class AdminConfigResponse(BaseModel):
    environment: str
    max_execution_timeout_seconds: int
    max_concurrency_per_workspace: int
    max_intelligence_depth: int
    max_intelligence_steps: int
    features_enabled: Dict[str, bool]

class AdminExportRequest(BaseModel):
    export_type: str  # "executions", "usage", "failures", "audit_logs"
    format: str = "json"  # "json", "csv"
    time_window: str = "24h"
    limit: int = 1000

class AdminExportResponse(BaseModel):
    export_type: str
    format: str
    record_count: int
    generated_at: datetime.datetime
    content: str
