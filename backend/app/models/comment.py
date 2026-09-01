import uuid
import datetime
from sqlalchemy import String, ForeignKey, Text, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from app.database.base_class import Base, AuditMixin

class Comment(Base, AuditMixin):
    __tablename__ = "comments"

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True) # document, workflow, agent
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    parent_comment_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"), nullable=True, index=True)
    
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True) # active, deleted
    
    edited_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    workspace = relationship("Workspace")
    author = relationship("User", foreign_keys=[author_id])
    project = relationship("Project", foreign_keys=[project_id])
    parent = relationship("Comment", remote_side="Comment.id", backref="replies")
    mentions = relationship("CommentMention", back_populates="comment", cascade="all, delete-orphan")

class CommentMention(Base):
    __tablename__ = "comment_mentions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    comment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"), nullable=False, index=True)
    mentioned_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

    comment = relationship("Comment", back_populates="mentions")
    mentioned_user = relationship("User")

    __table_args__ = (
        UniqueConstraint("comment_id", "mentioned_user_id", name="uq_comment_user_mention"),
    )
