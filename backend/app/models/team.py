import uuid
from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from app.database.base_class import Base, AuditMixin

class Team(Base, AuditMixin):
    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_team_workspace_name"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False) # active, archived
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), 
        nullable=True
    )

    workspace = relationship("Workspace", back_populates="teams")
    memberships = relationship("TeamMembership", back_populates="team", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])

class TeamMembership(Base, AuditMixin):
    __tablename__ = "team_memberships"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_membership_user"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    role: Mapped[str] = mapped_column(String(50), default="member", nullable=False) # owner, member
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False) # active, removed

    team = relationship("Team", back_populates="memberships")
    user = relationship("User")
