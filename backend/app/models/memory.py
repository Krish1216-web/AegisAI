import uuid
from sqlalchemy import String, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator
from typing import List, Optional
from app.database.base_class import Base, AuditMixin

# Custom pgvector type fallback for development / missing library
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    class Vector(TypeDecorator):
        impl = JSON
        cache_ok = True
        def __init__(self, dimensions=None):
            super().__init__()
            self.dimensions = dimensions

class MemoryCategory(Base, AuditMixin):
    __tablename__ = "memory_categories"
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    memories = relationship("Memory", back_populates="category")

class Memory(Base, AuditMixin):
    __tablename__ = "memories"
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memory_categories.id", ondelete="RESTRICT"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    category = relationship("MemoryCategory", back_populates="memories")
    embeddings = relationship("MemoryEmbedding", back_populates="memory", cascade="all, delete-orphan")

class MemoryEmbedding(Base, AuditMixin):
    __tablename__ = "memory_embeddings"
    memory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memories.id", ondelete="CASCADE"), nullable=False)
    vector_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True) # ID in Qdrant
    
    memory = relationship("Memory", back_populates="embeddings")

class AgentMemory(Base, AuditMixin):
    __tablename__ = "agent_memories"
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    importance: Mapped[float] = mapped_column(nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    meta_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    embedding: Mapped[Optional[list]] = mapped_column(Vector(1536), nullable=True)
