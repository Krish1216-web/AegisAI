import datetime
import uuid
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, declarative_base, declared_attr, mapped_column
from typing import Any, Optional

class BaseClass:
    __name__: str

    # Generate __tablename__ automatically using lowercase of class name
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

Base = declarative_base(cls=BaseClass)

class AuditMixin:
    """
    Mixin class providing standard enterprise tracking fields.
    """
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False
    )
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        nullable=True
    )
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        nullable=True
    )
