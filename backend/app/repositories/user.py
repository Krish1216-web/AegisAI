from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional, List
import uuid

from app.models.user import User
from app.models.role import Role

class RoleRepository:
    """
    Repository wrapper class for database actions on Role objects.
    """
    def __init__(self, db: Session):
        self.db = db

    def get_by_name(self, name: str) -> Optional[Role]:
        stmt = select(Role).where(Role.name == name)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, name: str, description: Optional[str] = None) -> Role:
        role = Role(name=name, description=description)
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

class UserRepository:
    """
    Repository wrapper class for database actions on User objects.
    """
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        stmt = select(User).where(User.id == user_id, User.is_deleted == False)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email, User.is_deleted == False)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_username(self, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username, User.is_deleted == False)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
