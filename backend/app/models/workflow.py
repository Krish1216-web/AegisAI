import uuid
from sqlalchemy import String, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from app.database.base_class import Base, AuditMixin

class Workflow(Base, AuditMixin):
    __tablename__ = "workflows"
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    nodes = relationship("WorkflowNode", back_populates="workflow", cascade="all, delete-orphan")
    executions = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")

class WorkflowNode(Base, AuditMixin):
    __tablename__ = "workflow_nodes"
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False) # orchestrator | agent | tool
    config_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    workflow = relationship("Workflow", back_populates="nodes")

class WorkflowExecution(Base, AuditMixin):
    __tablename__ = "workflow_executions"
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    
    workflow = relationship("Workflow", back_populates="executions")
    logs = relationship("WorkflowLog", back_populates="execution", cascade="all, delete-orphan")

class WorkflowLog(Base, AuditMixin):
    __tablename__ = "workflow_logs"
    execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    execution = relationship("WorkflowExecution", back_populates="logs")
