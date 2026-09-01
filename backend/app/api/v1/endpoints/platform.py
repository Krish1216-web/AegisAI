import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.core.platform.capability import CapabilityType
from app.schemas.platform import (
    PlatformStatusResponse,
    PlatformCapabilityListResponse,
    PlatformCapabilityResponse
)
from app.services.platform_service import PlatformService

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
