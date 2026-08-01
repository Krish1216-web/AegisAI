import uuid
from sqlalchemy import String, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from app.database.base_class import Base, AuditMixin

class MCPServer(Base, AuditMixin):
    __tablename__ = "mcp_servers"
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    tools = relationship("MCPTool", back_populates="server", cascade="all, delete-orphan")
    connections = relationship("MCPConnection", back_populates="server", cascade="all, delete-orphan")

class MCPTool(Base, AuditMixin):
    __tablename__ = "mcp_tools"
    server_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    server = relationship("MCPServer", back_populates="tools")

class MCPConnection(Base, AuditMixin):
    __tablename__ = "mcp_connections"
    server_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="disconnected", nullable=False)
    ping_latency_ms: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    server = relationship("MCPServer", back_populates="connections")
