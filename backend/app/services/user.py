from sqlalchemy.orm import Session
from loguru import logger
import uuid
from typing import Any

from app.repositories.user import UserRepository
from app.core.security import get_password_hash, verify_password
from app.core.exceptions import AegisBaseException
from app.schemas.user import UserUpdate, ChangePasswordRequest, UserSettingsUpdate

class UserService:
    """
    Service layer coordinates profile updates, password modifications, settings adjustments.
    """
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def update_profile(self, user_id: uuid.UUID, payload: UserUpdate) -> Any:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise AegisBaseException("User not found.", code="USER_NOT_FOUND")

        if payload.username:
            # Check username uniqueness if modified
            if payload.username != user.username:
                existing = self.user_repo.get_by_username(payload.username)
                if existing:
                    raise AegisBaseException("Username already in use.", code="PROFILE_UPDATE_FAILED")
                user.username = payload.username

        if payload.email:
            if payload.email != user.email:
                existing = self.user_repo.get_by_email(payload.email)
                if existing:
                    raise AegisBaseException("Email already in use.", code="PROFILE_UPDATE_FAILED")
                user.email = payload.email

        if payload.avatar_url is not None:
            user.avatar_url = payload.avatar_url

        return self.user_repo.update(user)

    def change_password(self, user_id: uuid.UUID, payload: ChangePasswordRequest):
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise AegisBaseException("User not found.", code="USER_NOT_FOUND")

        if not verify_password(payload.old_password, user.password_hash):
            raise AegisBaseException("Current password verification failed.", code="PASSWORD_CHANGE_FAILED")

        user.password_hash = get_password_hash(payload.new_password)
        self.user_repo.update(user)
        logger.info(f"Password modified successfully for user: {user.username}")

    def update_settings(self, user_id: uuid.UUID, payload: UserSettingsUpdate) -> Any:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise AegisBaseException("User not found.", code="USER_NOT_FOUND")

        current_settings = user.settings or {}
        
        # Merge new preference adjustments
        if payload.language:
            current_settings["language"] = payload.language
        if payload.theme:
            current_settings["theme"] = payload.theme
        if payload.timezone:
            current_settings["timezone"] = payload.timezone
        if payload.email_notifications is not None:
            current_settings["email_notifications"] = payload.email_notifications
        if payload.ai_preferences:
            current_settings["ai_preferences"] = payload.ai_preferences

        user.settings = current_settings
        return self.user_repo.update(user)

    def delete_account(self, user_id: uuid.UUID):
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise AegisBaseException("User not found.", code="USER_NOT_FOUND")

        user.is_deleted = True
        user.is_active = False
        self.user_repo.update(user)
        logger.info(f"Account marked for soft-deletion: {user_id}")
