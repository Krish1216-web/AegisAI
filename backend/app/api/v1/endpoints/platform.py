import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.core.platform.capability import CapabilityType
from app.core.platform.context import PlatformContext
from app.core.platform.security import SecurityContext, TrustLevel
from app.schemas.platform import (
    PlatformStatusResponse,
    PlatformCapabilityListResponse,
    PlatformCapabilityResponse,
    PlatformExecutionRequest,
    PlatformExecutionResponse,
    PlatformExecutionCancelRequest,
    PlatformIntelligenceRequest,
    PlatformIntelligenceResponse
)
from app.services.platform_service import PlatformService
from app.services.platform_execution import PlatformExecutionService

router = APIRouter(prefix="/platform", tags=["platform"])

@router.get("/status", response_model=PlatformStatusResponse)
def get_platform_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns Phase 8 platform runtime status, health, and enabled feature flags.
    """
    if not current_user.workspace_id:
        raise HTTPException(status_code=400, detail="User is not associated with an active workspace.")
    service = PlatformService(db)
    return service.get_platform_status(current_user.workspace_id)

@router.get("/capabilities", response_model=PlatformCapabilityListResponse)
def list_platform_capabilities(
    capability_type: Optional[CapabilityType] = Query(None, description="Optional capability type filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists all platform capabilities accessible to the current tenant.
    """
    if not current_user.workspace_id:
        raise HTTPException(status_code=400, detail="User is not associated with an active workspace.")
    service = PlatformService(db)
    user_role = current_user.role.name if current_user.role else "viewer"
    return service.list_capabilities(
        workspace_id=current_user.workspace_id,
        user_role=user_role,
        capability_type=capability_type
    )

@router.get("/capabilities/{capability_id}", response_model=PlatformCapabilityResponse)
def get_platform_capability(
    capability_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves metadata for a specific capability.
    """
    if not current_user.workspace_id:
        raise HTTPException(status_code=400, detail="User is not associated with an active workspace.")
    service = PlatformService(db)
    user_role = current_user.role.name if current_user.role else "viewer"
    cap = service.get_capability(
        workspace_id=current_user.workspace_id,
        capability_id=capability_id,
        user_role=user_role
    )
    if not cap:
        raise HTTPException(status_code=404, detail=f"Capability '{capability_id}' not found or inaccessible.")
    return PlatformCapabilityResponse(capability=cap)

@router.post("/execute", response_model=PlatformExecutionResponse)
def execute_capability(
    payload: PlatformExecutionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes a platform capability through the Core Platform Execution Engine.
    """
    if not current_user.workspace_id:
        raise HTTPException(status_code=400, detail="User is not associated with an active workspace.")
    
    user_role = current_user.role.name if current_user.role else "viewer"
    sec_ctx = SecurityContext(
        user_id=current_user.id,
        workspace_id=current_user.workspace_id,
        user_role=user_role,
        trust_level=TrustLevel.HIGH if user_role == "admin" else TrustLevel.MEDIUM
    )

    context = PlatformContext(
        user_id=current_user.id,
        workspace_id=current_user.workspace_id,
        security_context=sec_ctx,
        input_data=payload.input_data,
        metadata=payload.metadata
    )

    exec_service = PlatformExecutionService(db)
    result = exec_service.execute(
        capability_id=payload.capability_id,
        context=context,
        input_data=payload.input_data,
        idempotency_key=payload.idempotency_key,
        timeout_seconds=payload.timeout_seconds
    )
    return result

@router.get("/executions/{execution_id}", response_model=PlatformExecutionResponse)
def get_execution_status(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves status of a platform execution.
    """
    if not current_user.workspace_id:
        raise HTTPException(status_code=400, detail="User is not associated with an active workspace.")
    
    exec_service = PlatformExecutionService(db)
    result = exec_service.get_execution(execution_id, current_user.workspace_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Execution '{execution_id}' not found.")
    return result

@router.post("/executions/{execution_id}/cancel", response_model=PlatformExecutionResponse)
def cancel_execution(
    execution_id: str,
    payload: PlatformExecutionCancelRequest = PlatformExecutionCancelRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancels an active platform execution.
    """
    if not current_user.workspace_id:
        raise HTTPException(status_code=400, detail="User is not associated with an active workspace.")
    
    exec_service = PlatformExecutionService(db)
    result = exec_service.cancel_execution(
        execution_id=execution_id,
        user_id=current_user.id,
        workspace_id=current_user.workspace_id,
        reason=payload.reason
    )
    if not result:
        raise HTTPException(status_code=404, detail=f"Execution '{execution_id}' not found.")
    return result

@router.post("/intelligence/execute", response_model=PlatformIntelligenceResponse)
def execute_intelligence(
    payload: PlatformIntelligenceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Phase 8.7: Executes an intelligent multi-capability plan adaptively.
    """
    if not current_user.workspace_id:
        raise HTTPException(status_code=400, detail="User is not associated with an active workspace.")

    user_role = current_user.role.name if (current_user.role and hasattr(current_user.role, "name")) else "viewer"
    user_perms = {p.name for p in current_user.role.permissions} if (current_user.role and hasattr(current_user.role, "permissions") and current_user.role.permissions) else set()

    sec_ctx = SecurityContext(
        user_id=current_user.id,
        workspace_id=current_user.workspace_id,
        user_role=user_role,
        permissions=user_perms,
        trust_level=TrustLevel.HIGH if user_role == "admin" else TrustLevel.MEDIUM
    )
    context = PlatformContext(
        user_id=current_user.id,
        workspace_id=current_user.workspace_id,
        security_context=sec_ctx
    )

    from app.core.platform.intelligence.engine import AdvancedIntelligenceService
    from app.core.platform.intelligence.models import ExecutionMode

    valid_modes = {
        "adaptive": ExecutionMode.ADAPTIVE,
        "sequential": ExecutionMode.SEQUENTIAL,
        "parallel": ExecutionMode.PARALLEL
    }
    mode_key = (payload.mode or "").lower()
    if mode_key not in valid_modes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid execution mode '{payload.mode}'. Valid modes: {list(valid_modes.keys())}"
        )
    mode = valid_modes[mode_key]

    service = AdvancedIntelligenceService(db)
    result = service.execute_intelligent_query(
        query=payload.query,
        context=context,
        mode=mode,
        input_data=payload.input_data
    )
    return result

# ==================================================
# Phase 8.8: Observability & Analytics Endpoints
# ==================================================

from app.core.platform.observability import (
    TimeWindow,
    CapabilityHealth,
    PlatformOverviewMetrics,
    CapabilityAnalyticsResponse,
    LifecycleMetrics,
    BottleneckAnalyticsResponse,
    IntelligenceAnalytics,
    ProvenanceAnalytics,
    FailureAnalytics,
    AlertAnalyticsResponse,
    ExecutionTimeline,
    PlatformObservabilityService
)

def _validate_analytics_access(user: User) -> None:
    if not user.workspace_id:
        raise HTTPException(status_code=400, detail="User is not associated with an active workspace.")
    # Verify permission / role
    user_role = user.role.name if (user.role and hasattr(user.role, "name")) else (str(user.role) if user.role else "viewer")
    user_perms = {p.name for p in user.role.permissions} if (user.role and hasattr(user.role, "permissions") and user.role.permissions) else set()
    if user_role not in ["admin", "owner", "member", "viewer"] and "platform:analytics:view" not in user_perms:
        raise HTTPException(status_code=403, detail="Permission denied: platform:analytics:view required.")

def _validate_time_window(window_str: str) -> str:
    valid = ["1h", "24h", "7d", "30d"]
    if window_str not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid time window '{window_str}'. Supported windows: {valid}"
        )
    return window_str

@router.get("/analytics/overview", response_model=PlatformOverviewMetrics)
def get_analytics_overview(
    time_window: str = Query("24h", description="Time window: 1h, 24h, 7d, 30d"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _validate_analytics_access(current_user)
    tw = _validate_time_window(time_window)
    service = PlatformObservabilityService(db)
    return service.get_overview_metrics(current_user.workspace_id, time_window=tw)

@router.get("/analytics/capabilities", response_model=CapabilityAnalyticsResponse)
def get_analytics_capabilities(
    time_window: str = Query("24h", description="Time window: 1h, 24h, 7d, 30d"),
    capability_type: Optional[str] = Query(None, description="Optional capability type filter"),
    health: Optional[CapabilityHealth] = Query(None, description="Optional health filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _validate_analytics_access(current_user)
    tw = _validate_time_window(time_window)
    service = PlatformObservabilityService(db)
    return service.get_capability_performance(
        workspace_id=current_user.workspace_id,
        time_window=tw,
        capability_type=capability_type,
        health_filter=health
    )

@router.get("/analytics/lifecycle", response_model=LifecycleMetrics)
def get_analytics_lifecycle(
    time_window: str = Query("24h", description="Time window: 1h, 24h, 7d, 30d"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _validate_analytics_access(current_user)
    tw = _validate_time_window(time_window)
    service = PlatformObservabilityService(db)
    return service.get_lifecycle_metrics(current_user.workspace_id, time_window=tw)

@router.get("/analytics/failures", response_model=FailureAnalytics)
def get_analytics_failures(
    time_window: str = Query("24h", description="Time window: 1h, 24h, 7d, 30d"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _validate_analytics_access(current_user)
    tw = _validate_time_window(time_window)
    service = PlatformObservabilityService(db)
    return service.get_failure_analytics(current_user.workspace_id, time_window=tw)

@router.get("/analytics/intelligence", response_model=IntelligenceAnalytics)
def get_analytics_intelligence(
    time_window: str = Query("24h", description="Time window: 1h, 24h, 7d, 30d"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _validate_analytics_access(current_user)
    tw = _validate_time_window(time_window)
    service = PlatformObservabilityService(db)
    return service.get_intelligence_analytics(current_user.workspace_id, time_window=tw)

@router.get("/analytics/provenance", response_model=ProvenanceAnalytics)
def get_analytics_provenance(
    time_window: str = Query("24h", description="Time window: 1h, 24h, 7d, 30d"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _validate_analytics_access(current_user)
    tw = _validate_time_window(time_window)
    service = PlatformObservabilityService(db)
    return service.get_provenance_analytics(current_user.workspace_id, time_window=tw)

@router.get("/analytics/bottlenecks", response_model=BottleneckAnalyticsResponse)
def get_analytics_bottlenecks(
    time_window: str = Query("24h", description="Time window: 1h, 24h, 7d, 30d"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _validate_analytics_access(current_user)
    tw = _validate_time_window(time_window)
    service = PlatformObservabilityService(db)
    return service.get_bottleneck_analytics(current_user.workspace_id, time_window=tw)

@router.get("/analytics/alerts", response_model=AlertAnalyticsResponse)
def get_analytics_alerts(
    time_window: str = Query("24h", description="Time window: 1h, 24h, 7d, 30d"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _validate_analytics_access(current_user)
    tw = _validate_time_window(time_window)
    service = PlatformObservabilityService(db)
    return service.get_alerts(current_user.workspace_id, time_window=tw)

@router.get("/analytics/executions/{execution_id}/timeline", response_model=ExecutionTimeline)
def get_execution_timeline(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _validate_analytics_access(current_user)
    service = PlatformObservabilityService(db)
    timeline = service.get_execution_timeline(execution_id, current_user.workspace_id)
    if not timeline:
        raise HTTPException(status_code=404, detail=f"Execution timeline for '{execution_id}' not found.")
    return timeline
