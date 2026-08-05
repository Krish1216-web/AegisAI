from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.user import UserResponse, UserUpdate, ChangePasswordRequest, UserSettingsUpdate
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["User Management"])

@router.put("/me", response_model=UserResponse)
def update_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates the authenticated user's email, username, or avatar URL.
    """
    user_service = UserService(db)
    return user_service.update_profile(current_user.id, payload)

@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Allows the user to modify their authentication credentials.
    """
    user_service = UserService(db)
    user_service.change_password(current_user.id, payload)

@router.put("/me/settings", response_model=UserResponse)
def update_settings(
    payload: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Saves theme configurations, timezone parameters, and custom AI preferences.
    """
    user_service = UserService(db)
    return user_service.update_settings(current_user.id, payload)

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Soft-deletes the authenticated user's account and revokes active sessions.
    """
    user_service = UserService(db)
    user_service.delete_account(current_user.id)
