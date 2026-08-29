import uuid
from sqlalchemy import String, ForeignKey, JSON, Integer, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional, Any
from app.database.base_class import Base, AuditMixin

class RAGQuery(Base, AuditMixin):
    __tablename__ = "rag_queries"
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    
    query: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    
    citations: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    retrieved_chunks: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    is_cached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
