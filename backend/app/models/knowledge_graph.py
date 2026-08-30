import uuid
from enum import Enum
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Text, ForeignKey, JSON, Float, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base_class import Base, AuditMixin

class NodeType(str, Enum):
    USER = "USER"
    WORKSPACE = "WORKSPACE"
    DOCUMENT = "DOCUMENT"
    DOCUMENT_CHUNK = "DOCUMENT_CHUNK"
    PROJECT = "PROJECT"
    SKILL = "SKILL"
    CONVERSATION = "CONVERSATION"
    MEMORY = "MEMORY"
    TASK = "TASK"
    AGENT = "AGENT"

class RelationshipType(str, Enum):
    OWNS = "OWNS"
    BELONGS_TO = "BELONGS_TO"
    PART_OF = "PART_OF"
    RELATED_TO = "RELATED_TO"
    CONTAINS = "CONTAINS"
    MENTIONS = "MENTIONS"
    REFERENCES = "REFERENCES"
    HAS_MEMORY = "HAS_MEMORY"
    ASSIGNED_TO = "ASSIGNED_TO"
    EXECUTED = "EXECUTED"
    USES = "USES"
    DEPENDS_ON = "DEPENDS_ON"
    CREATED_BY = "CREATED_BY"
    WORKS_ON = "WORKS_ON"

class KnowledgeGraphNode(Base, AuditMixin):
    __tablename__ = "knowledge_graph_nodes"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    
    node_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Mapped to 'metadata' column in DB
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSON, nullable=True)

    outgoing_edges = relationship(
        "KnowledgeGraphEdge",
        foreign_keys="KnowledgeGraphEdge.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan"
    )
    incoming_edges = relationship(
        "KnowledgeGraphEdge",
        foreign_keys="KnowledgeGraphEdge.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_kg_nodes_ws_type", "workspace_id", "node_type"),
        Index("ix_kg_nodes_ws_ext", "workspace_id", "external_id"),
        Index("ix_kg_nodes_user_ws", "user_id", "workspace_id"),
    )

class KnowledgeGraphEdge(Base, AuditMixin):
    __tablename__ = "knowledge_graph_edges"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    
    # Mapped to 'properties' column in DB
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column("properties", JSON, nullable=True)

    source_node = relationship("KnowledgeGraphNode", foreign_keys=[source_node_id], back_populates="outgoing_edges")
    target_node = relationship("KnowledgeGraphNode", foreign_keys=[target_node_id], back_populates="incoming_edges")

    __table_args__ = (
        UniqueConstraint("source_node_id", "target_node_id", "relationship_type", name="uq_kg_edges_src_tgt_rel"),
        Index("ix_kg_edges_ws_user", "workspace_id", "user_id"),
        Index("ix_kg_edges_src_type", "source_node_id", "relationship_type"),
        Index("ix_kg_edges_tgt_type", "target_node_id", "relationship_type"),
    )
