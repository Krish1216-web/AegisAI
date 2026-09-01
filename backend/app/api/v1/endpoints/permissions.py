from fastapi import APIRouter, Depends
from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.workspace import PermissionRegistryResponse
from app.core.auth.permissions import ALL_PERMISSIONS, WORKSPACE_ROLE_PERMISSIONS, TEAM_ROLE_OVERLAY

router = APIRouter(prefix="/permissions", tags=["Permissions & Roles Registry"])

@router.get("", response_model=PermissionRegistryResponse)
def get_permission_registry(
    current_user: User = Depends(get_current_user)
):
    ws_roles_serializable = {
        role: sorted(list(perms)) for role, perms in WORKSPACE_ROLE_PERMISSIONS.items()
    }
    team_roles_serializable = {
        role: sorted(list(perms)) for role, perms in TEAM_ROLE_OVERLAY.items()
    }

    return PermissionRegistryResponse(
        permissions=sorted(list(ALL_PERMISSIONS)),
        workspace_roles=ws_roles_serializable,
        team_roles=team_roles_serializable
    )
