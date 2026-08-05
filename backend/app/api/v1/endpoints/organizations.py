from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
import uuid

from app.database.session import get_db
from app.schemas.workspace import OrganizationResponse, OrganizationCreate, OrganizationUpdate
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.workspace import WorkspaceService

router = APIRouter(prefix="/organizations", tags=["Organization Management"])

@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Registers a new tenant organization in the database.
    """
    ws_service = WorkspaceService(db)
    return ws_service.create_organization(payload.name, current_user.id)

@router.put("/{organization_id}", response_model=OrganizationResponse)
def update_organization(
    organization_id: uuid.UUID,
    payload: OrganizationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Modifies organization specifications.
    """
    ws_service = WorkspaceService(db)
    return ws_service.update_organization(organization_id, payload.name)
