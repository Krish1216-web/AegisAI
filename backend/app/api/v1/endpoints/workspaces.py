from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
import uuid

from app.database.session import get_db
from app.schemas.workspace import WorkspaceResponse, WorkspaceCreate, WorkspaceUpdate, WorkspaceMemberResponse, WorkspaceMemberCreate
from app.api.dependencies import get_current_user, get_workspace_member
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.services.workspace import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["Workspace Management"])

@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Spawns a new workspace associated with the target organization.
    """
    ws_service = WorkspaceService(db)
    return ws_service.create_workspace(payload.name, payload.organization_id, current_user.id)

@router.put("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    current_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    """
    Updates workspace details (requires workspace membership).
    """
    if current_member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires owner or admin permissions to modify workspace details."
        )
    ws_service = WorkspaceService(db)
    return ws_service.update_workspace(workspace_id, payload.name)

@router.post("/{workspace_id}/members", response_model=WorkspaceMemberResponse, status_code=status.HTTP_201_CREATED)
def add_member(
    workspace_id: uuid.UUID,
    payload: WorkspaceMemberCreate,
    current_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    """
    Invites a user to join the workspace.
    """
    if current_member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires owner or admin permissions to manage membership roles."
        )
    ws_service = WorkspaceService(db)
    return ws_service.add_workspace_member(workspace_id, payload.user_id, payload.role)

@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    current_member: WorkspaceMember = Depends(get_workspace_member),
    db: Session = Depends(get_db)
):
    """
    Evicts a member from the workspace team.
    """
    if current_member.role not in ["owner", "admin"] and current_member.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden."
        )
    ws_service = WorkspaceService(db)
    ws_service.remove_workspace_member(workspace_id, user_id)
