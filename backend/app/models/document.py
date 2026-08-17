import uuid
from sqlalchemy import String, Integer, ForeignKey, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from app.database.base_class import Base, AuditMixin

class Document(Base, AuditMixin):
    __tablename__ = "documents"
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(10), nullable=False)
    
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="UPLOADED", nullable=False)
    
    # Document details
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Media details
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Processing metrics
    extracted_text_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processing_error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Raw extensible metadata payload, mapped to column "metadata"
    meta_data: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    embeddings = relationship("DocumentEmbedding", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base, AuditMixin):
    __tablename__ = "document_chunks"
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    
    document = relationship("Document", back_populates="chunks")

class DocumentEmbedding(Base, AuditMixin):
    __tablename__ = "document_embeddings"
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    vector_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True) # ID in Qdrant
    
    document = relationship("Document", back_populates="embeddings")
