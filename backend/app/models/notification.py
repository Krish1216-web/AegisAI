import uuid
import datetime
from sqlalchemy import String, Text, ForeignKey, Boolean, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from app.database.base_class import Base, AuditMixin

class Notification(Base, AuditMixin):
    __tablename__ = "notifications"

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=True, index=True)
    comment_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"), nullable=True, index=True)
    mention_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("comment_mentions.id", ondelete="CASCADE"), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(20), default="unread", nullable=False, index=True) # unread, read
    read_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    workspace = relationship("Workspace")
    recipient = relationship("User", foreign_keys=[recipient_user_id])
    actor = relationship("User", foreign_keys=[actor_user_id])
    project = relationship("Project", foreign_keys=[project_id])
    team = relationship("Team", foreign_keys=[team_id])
    comment = relationship("Comment", foreign_keys=[comment_id])

class NotificationPreference(Base, AuditMixin):
    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True)
    notification_type: Mapped[str] = mapped_column(String(50), default="all", nullable=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user = relationship("User")
    workspace = relationship("Workspace")

    __table_args__ = (
        UniqueConstraint("user_id", "workspace_id", "notification_type", name="uq_user_ws_notif_type"),
    )
