import uuid
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from app.database.base_class import Base, AuditMixin

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
