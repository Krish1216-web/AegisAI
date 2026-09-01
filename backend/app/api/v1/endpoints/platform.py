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

    user_role = current_user.role.name if current_user.role else "viewer"
    user_perms = {p.name for p in current_user.role.permissions} if current_user.role and current_user.role.permissions else set()

    sec_ctx = SecurityContext(
        user_id=current_user.id,
        workspace_id=current_user.workspace_id,
        user_role=user_role,
        permissions=user_perms,
        trust_level=TrustLevel.AUTHENTICATED
    )
    context = PlatformContext(
        user_id=current_user.id,
        workspace_id=current_user.workspace_id,
        security_context=sec_ctx
    )

    from app.core.platform.intelligence.engine import AdvancedIntelligenceService
    from app.core.platform.intelligence.models import ExecutionMode

    mode = ExecutionMode.ADAPTIVE
    if payload.mode.lower() == "sequential":
        mode = ExecutionMode.SEQUENTIAL
    elif payload.mode.lower() == "parallel":
        mode = ExecutionMode.PARALLEL

    service = AdvancedIntelligenceService(db)
    result = service.execute_intelligent_query(
        query=payload.query,
        context=context,
        mode=mode,
        input_data=payload.input_data
    )
    return result
