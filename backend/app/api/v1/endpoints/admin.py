import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.platform_admin import PlatformAdminService
from app.schemas.admin import (
    AdminOverviewResponse,
    AdminUserListResponse,
    AdminUserDetailResponse,
    AdminUserStatusUpdateRequest,
    AdminUserRoleUpdateRequest,
    AdminWorkspaceListResponse,
    AdminRolePermissionResponse,
    AdminSystemHealthResponse,
    AdminExecutionListResponse,
    AdminAuditLogListResponse,
    AdminSecurityPostureResponse,
    AdminActivityFeedResponse,
    AdminConfigResponse,
    AdminExportRequest,
    AdminExportResponse
)

router = APIRouter(prefix="/admin", tags=["Platform Administration"])

def _require_admin(user: User) -> None:
    """Strict authorization gate for admin endpoints."""
    role_name = user.role.name if (user.role and hasattr(user.role, "name")) else (str(user.role) if user.role else "viewer")
    perms = {p.name for p in user.role.permissions} if (user.role and hasattr(user.role, "permissions") and user.role.permissions) else set()
    
    if role_name.lower() not in ["admin", "super admin", "owner"] and "platform:admin:view" not in perms and "platform:admin:write" not in perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Administrative privileges required."
        )

@router.get("/overview", response_model=AdminOverviewResponse)
def get_admin_overview(
    time_window: str = Query("24h", description="Time window: 1h, 24h, 7d, 30d"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns live system-wide and tenant-aware enterprise admin metrics.
    """
    _require_admin(current_user)
    service = PlatformAdminService(db)
    return service.get_admin_overview(current_user.workspace_id, time_window=time_window)

@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Paginated user operations control: search, filter, and inspect user profiles.
    """
    _require_admin(current_user)
    service = PlatformAdminService(db)
    return service.list_users(page=page, page_size=page_size, search=search, role=role, is_active=is_active)

@router.get("/users/{user_id}", response_model=AdminUserDetailResponse)
def get_user_detail(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Inspect detailed user profile, role, workspace memberships, and recent audit activity.
    """
    _require_admin(current_user)
    service = PlatformAdminService(db)
    user_detail = service.get_user_detail(user_id)
    if not user_detail:
        raise HTTPException(status_code=404, detail="User not found.")
    return user_detail

@router.put("/users/{user_id}/status")
def update_user_status(
    user_id: uuid.UUID,
    payload: AdminUserStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Activate or suspend a user account with persistent audit trail.
    """
    _require_admin(current_user)
    service = PlatformAdminService(db)
    user = service.update_user_status(user_id, payload.is_active, current_user.id, payload.reason)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"message": "User status updated successfully", "user_id": str(user.id), "is_active": user.is_active}

@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: uuid.UUID,
    payload: AdminUserRoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change user authorization role with persistent audit trail.
    """
    _require_admin(current_user)
    service = PlatformAdminService(db)
    user = service.update_user_role(user_id, payload.role_name, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"message": "User role updated successfully", "user_id": str(user.id), "role": payload.role_name}

@router.get("/workspaces", response_model=AdminWorkspaceListResponse)
def list_workspaces(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Paginated workspace administration: inspect members, documents, workflows, and MCP usage.
    """
    _require_admin(current_user)
    service = PlatformAdminService(db)
    return service.list_workspaces(page=page, page_size=page_size, search=search)

@router.get("/roles-permissions", response_model=AdminRolePermissionResponse)
def get_roles_and_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Inspect global RBAC roles, permission matrix, and capability permission requirements.
    """
    _require_admin(current_user)
    service = PlatformAdminService(db)
    return service.get_roles_and_permissions()

@router.get("/system-health", response_model=AdminSystemHealthResponse)
def get_system_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Centralized system health checking: Database, Redis, Registry, Execution Engine, Events, MCP, Workflows, Intelligence.
    """
    _require_admin(current_user)
    service = PlatformAdminService(db)
    return service.get_system_health()

@router.get("/executions", response_model=AdminExecutionListResponse)
def list_executions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    capability_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Administrative execution monitoring: search and filter all platform executions.
    """
    _require_admin(current_user)
    service = PlatformAdminService(db)
    return service.list_executions(
        page=page,
        page_size=page_size,
        workspace_id=current_user.workspace_id,
        capability_id=capability_id,
        status_filter=status_filter,
        search=search
    )

@router.get("/audit-logs", response_model=AdminAuditLogListResponse)
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[uuid.UUID] = Query(None),
    action: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Query persistent security and administrative audit trails.
    """
    _require_admin(current_user)
    service = PlatformAdminService(db)
    return service.list_audit_logs(page=page, page_size=page_size, user_id=user_id, action=action, search=search)

@router.get("/security-posture", response_model=AdminSecurityPostureResponse)
def get_security_posture(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Inspect tenant isolation enforcement, RBAC posture, confirmation gates, SSRF defense, and denial logs.
    """
    _require_admin(current_user)
    service = PlatformAdminService(db)
    return service.get_security_posture(current_user.workspace_id)

@router.get("/activity-feed", response_model=AdminActivityFeedResponse)
def get_activity_feed(
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Unified activity stream across executions, administrative actions, and system events.
    """
    _require_admin(current_user)
    service = PlatformAdminService(db)
    return service.get_activity_feed(limit=limit, workspace_id=current_user.workspace_id)

@router.get("/config", response_model=AdminConfigResponse)
def get_admin_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Safe administrative inspection of platform limits, timeouts, and feature flags.
    """
    _require_admin(current_user)
    service = PlatformAdminService(db)
    return service.get_config()

@router.post("/export", response_model=AdminExportResponse)
def export_admin_report(
    payload: AdminExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate bounded CSV or JSON exports for executions, usage metrics, failures, or audit logs.
    """
    _require_admin(current_user)
    service = PlatformAdminService(db)
    return service.export_report(
        export_type=payload.export_type,
        fmt=payload.format,
        time_window=payload.time_window,
        limit=payload.limit,
        workspace_id=current_user.workspace_id
    )

# ============================================================================
# SECURITY OBSERVABILITY & COMPLIANCE ENDPOINTS (PHASE 10.9)
# ============================================================================

from app.services.security_observability import SecurityObservabilityService
from app.core.security_events import SecurityEventType, SecuritySeverity
from app.schemas.security_observability import (
    SecurityEventListResponse,
    SecurityAlertListResponse,
    SecurityMetricsResponse,
    IncidentEvidenceResponse,
    AuditIntegrityResponse,
    RetentionPolicyResponse
)

@router.get("/security/events", response_model=SecurityEventListResponse)
def list_security_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: Optional[SecuritySeverity] = Query(None),
    event_type: Optional[SecurityEventType] = Query(None),
    search: Optional[str] = Query(None),
    workspace_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Query tamper-evident security events with multi-tenant isolation and redaction.
    """
    _require_admin(current_user)
    # If not Super Admin / Platform Admin, enforce user's workspace
    target_ws = workspace_id if (current_user.role and current_user.role.name.lower() in ["super admin", "admin"]) else current_user.workspace_id
    service = SecurityObservabilityService(db)
    return service.list_events(
        page=page,
        page_size=page_size,
        workspace_id=target_ws,
        severity=severity,
        event_type=event_type,
        search=search
    )

@router.get("/security/alerts", response_model=SecurityAlertListResponse)
def list_security_alerts(
    severity: Optional[SecuritySeverity] = Query(None),
    status_filter: Optional[str] = Query("ACTIVE"),
    workspace_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Inspect real-time security alerts with anomaly detection and deduplication.
    """
    _require_admin(current_user)
    target_ws = workspace_id if (current_user.role and current_user.role.name.lower() in ["super admin", "admin"]) else current_user.workspace_id
    service = SecurityObservabilityService(db)
    alerts = service.alert_engine.get_alerts(
        workspace_id=target_ws,
        severity=severity,
        status_filter=status_filter
    )
    return SecurityAlertListResponse(total=len(alerts), alerts=alerts)

@router.get("/security/metrics", response_model=SecurityMetricsResponse)
def get_security_metrics(
    time_window: str = Query("24h", description="Time window: 1h, 24h, 7d, 30d"),
    workspace_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Aggregated operational security metrics across authentication, authorization, SSRF, MCP, and prompt injection.
    """
    _require_admin(current_user)
    target_ws = workspace_id if (current_user.role and current_user.role.name.lower() in ["super admin", "admin"]) else current_user.workspace_id
    service = SecurityObservabilityService(db)
    return service.get_security_metrics(workspace_id=target_ws, time_window=time_window)

@router.get("/security/incident-lookup", response_model=IncidentEvidenceResponse)
def lookup_incident_evidence(
    param: str = Query(..., description="Parameter: correlation_id, execution_id, request_id, actor_id, event_id"),
    value: str = Query(..., description="Target search identifier value"),
    workspace_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    End-to-end incident investigation correlating User -> Request -> Security Event -> Execution -> Audit evidence.
    """
    _require_admin(current_user)
    target_ws = workspace_id if (current_user.role and current_user.role.name.lower() in ["super admin", "admin"]) else current_user.workspace_id
    service = SecurityObservabilityService(db)
    return service.lookup_incident_evidence(query_param=param, query_value=value, workspace_id=target_ws)

@router.get("/security/audit-integrity", response_model=AuditIntegrityResponse)
def verify_audit_integrity(
    workspace_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cryptographic SHA-256 audit chain verification proving tamper-evidence and chain unbrokenness.
    """
    _require_admin(current_user)
    target_ws = workspace_id if (current_user.role and current_user.role.name.lower() in ["super admin", "admin"]) else current_user.workspace_id
    service = SecurityObservabilityService(db)
    return service.verify_integrity(workspace_id=target_ws)

@router.post("/security/retention/dry-run", response_model=RetentionPolicyResponse)
def inspect_retention_policy(
    retention_days: int = Query(90, ge=1, le=3650),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Dry-run inspection of records eligible for retention lifecycle without modifying data.
    """
    _require_admin(current_user)
    service = SecurityObservabilityService(db)
    return service.inspect_retention(retention_days=retention_days)

@router.post("/security/retention/apply")
def apply_retention_policy(
    retention_days: int = Query(90, ge=1, le=3650),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bounded, authorized purge of expired operational records with persistent administrative audit trail.
    """
    _require_admin(current_user)
    service = SecurityObservabilityService(db)
    purged_count = service.apply_retention(retention_days=retention_days, admin_user_id=current_user.id)
    return {
        "message": f"Retention policy applied: {purged_count} records purged older than {retention_days} days.",
        "purged_count": purged_count,
        "retention_days": retention_days,
        "executed_by": str(current_user.id)
    }
