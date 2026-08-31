import uuid
import enum
import datetime
from sqlalchemy import String, Boolean, ForeignKey, Text, JSON, DateTime, Enum, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, Dict, Any
from app.database.base_class import Base, AuditMixin

class WorkflowStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"

class WorkflowExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class WorkflowNodeStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"

class WorkflowNodeType(str, enum.Enum):
    START = "start"
    END = "end"
    AGENT = "agent"
    RAG = "rag"
    GRAPH = "graph"
    MEMORY = "memory"
    MCP_TOOL = "mcp_tool"
    MCP_RESOURCE = "mcp_resource"
    MCP_PROMPT = "mcp_prompt"
    LOCAL_TOOL = "local_tool"
    CONDITION = "condition"
    HUMAN_APPROVAL = "human_approval"
    TRANSFORM = "transform"

class Workflow(Base, AuditMixin):
    __tablename__ = "workflows"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=WorkflowStatus.DRAFT,
        nullable=False,
        index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    nodes = relationship("WorkflowNode", back_populates="workflow", cascade="all, delete-orphan", order_by="WorkflowNode.created_at")
    edges = relationship("WorkflowEdge", back_populates="workflow", cascade="all, delete-orphan")
    variables = relationship("WorkflowVariable", back_populates="workflow", cascade="all, delete-orphan")
    executions = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("workspace_id", "name", "deleted_at", name="uq_workspace_workflow_name"),
    )

class WorkflowNode(Base, AuditMixin):
    __tablename__ = "workflow_nodes"

    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    node_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    node_type: Mapped[WorkflowNodeType] = mapped_column(
        Enum(WorkflowNodeType, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    position: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    workflow = relationship("Workflow", back_populates="nodes")
    incoming_edges = relationship("WorkflowEdge", foreign_keys="WorkflowEdge.target_node_id", back_populates="target_node", cascade="all, delete-orphan")
    outgoing_edges = relationship("WorkflowEdge", foreign_keys="WorkflowEdge.source_node_id", back_populates="source_node", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("workflow_id", "node_key", "deleted_at", name="uq_workflow_node_key"),
    )

class WorkflowEdge(Base, AuditMixin):
    __tablename__ = "workflow_edges"

    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    source_node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    target_node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    condition: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    workflow = relationship("Workflow", back_populates="edges")
    source_node = relationship("WorkflowNode", foreign_keys=[source_node_id], back_populates="outgoing_edges")
    target_node = relationship("WorkflowNode", foreign_keys=[target_node_id], back_populates="incoming_edges")

    __table_args__ = (
        UniqueConstraint("workflow_id", "source_node_id", "target_node_id", "deleted_at", name="uq_workflow_edge"),
    )

class WorkflowVariable(Base, AuditMixin):
    __tablename__ = "workflow_variables"

    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_type: Mapped[str] = mapped_column(String(50), default="string", nullable=False)  # string, number, boolean, json
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    workflow = relationship("Workflow", back_populates="variables")

    __table_args__ = (
        UniqueConstraint("workflow_id", "name", "deleted_at", name="uq_workflow_variable_name"),
    )

class WorkflowExecution(Base, AuditMixin):
    __tablename__ = "workflow_executions"

    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)

    status: Mapped[WorkflowExecutionStatus] = mapped_column(
        Enum(WorkflowExecutionStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=WorkflowExecutionStatus.PENDING,
        nullable=False,
        index=True
    )
    input_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    output_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    workflow = relationship("Workflow", back_populates="executions")
    execution_nodes = relationship("WorkflowExecutionNode", back_populates="execution", cascade="all, delete-orphan", order_by="WorkflowExecutionNode.created_at")

class WorkflowExecutionNode(Base, AuditMixin):
    __tablename__ = "workflow_execution_nodes"

    execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("workflow_nodes.id", ondelete="SET NULL"), nullable=True, index=True)
    node_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    status: Mapped[WorkflowNodeStatus] = mapped_column(
        Enum(WorkflowNodeStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=WorkflowNodeStatus.PENDING,
        nullable=False,
        index=True
    )
    input_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    execution = relationship("WorkflowExecution", back_populates="execution_nodes")

# Compatibility alias for legacy schema lookups
WorkflowLog = WorkflowExecutionNode
