import uuid
import enum
import datetime
from sqlalchemy import String, Boolean, ForeignKey, Text, JSON, DateTime, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, Dict, Any
from app.database.base_class import Base, AuditMixin

class MCPTransport(str, enum.Enum):
    SSE = "sse"
    STREAMABLE_HTTP = "streamable_http"
    STDIO = "stdio"

class MCPServerStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    DISABLED = "disabled"

class MCPCapabilityType(str, enum.Enum):
    TOOL = "tool"
    RESOURCE = "resource"
    PROMPT = "prompt"

class MCPAuthenticationType(str, enum.Enum):
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    OAUTH = "oauth"

class MCPServer(Base, AuditMixin):
    __tablename__ = "mcp_servers"
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    server_url: Mapped[str] = mapped_column(String(512), nullable=False)
    
    transport: Mapped[MCPTransport] = mapped_column(
        Enum(MCPTransport, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=MCPTransport.SSE,
        nullable=False
    )
    status: Mapped[MCPServerStatus] = mapped_column(
        Enum(MCPServerStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=MCPServerStatus.INACTIVE,
        nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    authentication_type: Mapped[MCPAuthenticationType] = mapped_column(
        Enum(MCPAuthenticationType, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=MCPAuthenticationType.NONE,
        nullable=False
    )
    auth_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSON, nullable=True)
    
    last_connected_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    capabilities = relationship("MCPCapability", back_populates="server", cascade="all, delete-orphan")
    user = relationship("User", foreign_keys=[user_id])
    workspace = relationship("Workspace", foreign_keys=[workspace_id])

    __table_args__ = (
        UniqueConstraint('workspace_id', 'name', name='uq_mcp_servers_workspace_name'),
    )

class MCPCapability(Base, AuditMixin):
    __tablename__ = "mcp_capabilities"
    
    server_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False, index=True)
    
    capability_type: Mapped[MCPCapabilityType] = mapped_column(
        Enum(MCPCapabilityType, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    input_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    server = relationship("MCPServer", back_populates="capabilities")

    __table_args__ = (
        UniqueConstraint('server_id', 'capability_type', 'name', name='uq_mcp_capability_server_type_name'),
    )
