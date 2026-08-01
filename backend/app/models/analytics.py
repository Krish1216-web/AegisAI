import uuid
from sqlalchemy import String, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from app.database.base_class import Base, AuditMixin

class AnalyticsEvent(Base, AuditMixin):
    __tablename__ = "analytics_events"
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class UsageMetrics(Base, AuditMixin):
    __tablename__ = "usage_metrics"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    queries_run: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

class APIUsage(Base, AuditMixin):
    __tablename__ = "api_usages"
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
