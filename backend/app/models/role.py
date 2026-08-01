import uuid
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base_class import Base

class Role(Base):
    """
    SQLAlchemy Model representing user roles for RBAC.
    """
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationship back to Users
    users = relationship("User", back_populates="role")
