import uuid
import datetime
from sqlalchemy import String, ForeignKey, Text, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from app.database.base_class import Base, AuditMixin

class Project(Base, AuditMixin):
    __tablename__ = "projects"
    
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    workspace = relationship("Workspace", backref="projects")
    creator = relationship("User", foreign_keys=[created_by])
    members = relationship("ProjectMembership", back_populates="project", cascade="all, delete-orphan")
    resources = relationship("ProjectResource", back_populates="project", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_workspace_project_name"),
    )

class ProjectMembership(Base, AuditMixin):
    __tablename__ = "project_memberships"
    
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), default="viewer", nullable=False) # owner, editor, viewer
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True) # active, removed
    
    project = relationship("Project", back_populates="members")
    user = relationship("User")
    
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_user_membership"),
    )

class ProjectResource(Base, AuditMixin):
    __tablename__ = "project_resources"
    
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # document, workflow, agent
    resource_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    project = relationship("Project", back_populates="resources")
    
    __table_args__ = (
        UniqueConstraint("project_id", "resource_type", "resource_id", name="uq_project_resource_link"),
    )
