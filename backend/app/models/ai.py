import uuid
import datetime
from sqlalchemy import String, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from app.database.base_class import Base, AuditMixin

class Agent(Base, AuditMixin):
    __tablename__ = "agents"
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    
    executions = relationship("AgentExecution", back_populates="agent", cascade="all, delete-orphan")

class AgentExecution(Base, AuditMixin):
    __tablename__ = "agent_executions"
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    input_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    agent = relationship("Agent", back_populates="executions")
    logs = relationship("AgentLog", back_populates="execution", cascade="all, delete-orphan")

class AgentLog(Base, AuditMixin):
    __tablename__ = "agent_logs"
    execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_executions.id", ondelete="CASCADE"), nullable=False)
    log_level: Mapped[str] = mapped_column(String(20), default="info", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    execution = relationship("AgentExecution", back_populates="logs")
