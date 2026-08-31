import uuid
import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models.mcp import MCPTransport, MCPServerStatus, MCPCapabilityType, MCPAuthenticationType
from app.core.mcp.security import CredentialStore

class MCPServerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Unique human-readable server name")
    description: Optional[str] = Field(None, max_length=1000, description="Description of the server purpose")
    server_url: str = Field(..., max_length=512, description="Target MCP connection URL or command path")
    transport: MCPTransport = Field(default=MCPTransport.SSE, description="Transport protocol: sse, streamable_http, stdio")
    authentication_type: MCPAuthenticationType = Field(default=MCPAuthenticationType.NONE, description="Auth scheme")
    auth_config: Optional[Dict[str, Any]] = Field(default=None, description="Auth credentials and tokens")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Custom metadata tags")

class MCPServerCreate(MCPServerBase):
    pass

class MCPServerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    server_url: Optional[str] = Field(None, max_length=512)
    transport: Optional[MCPTransport] = None
    authentication_type: Optional[MCPAuthenticationType] = None
    auth_config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None

class MCPCapabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    server_id: uuid.UUID
    capability_type: MCPCapabilityType
    name: str
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="meta_data")
    enabled: bool
    definition_hash: Optional[str] = None
    is_stale: bool = False
    stale_at: Optional[datetime.datetime] = None
    first_discovered_at: Optional[datetime.datetime] = None
    last_discovered_at: Optional[datetime.datetime] = None
    version: int = 1
    created_at: datetime.datetime
    updated_at: datetime.datetime

class MCPServerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: Optional[str] = None
    server_url: str
    transport: MCPTransport
    status: MCPServerStatus
    enabled: bool
    authentication_type: MCPAuthenticationType
    auth_config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="meta_data")
    server_version: Optional[str] = None
    protocol_version: Optional[str] = "2024-11-05"
    last_connected_at: Optional[datetime.datetime] = None
    last_health_check_at: Optional[datetime.datetime] = None
    last_discovery_at: Optional[datetime.datetime] = None
    last_error: Optional[str] = None
    capabilities_count: int = 0
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @field_validator("auth_config", mode="before")
    @classmethod
    def mask_credentials(cls, v: Any) -> Any:
        if isinstance(v, dict):
            return CredentialStore.sanitize_auth_config(v)
        return v

class MCPServerListResponse(BaseModel):
    servers: List[MCPServerResponse]
    total: int

class MCPCapabilityListResponse(BaseModel):
    capabilities: List[MCPCapabilityResponse]
    total: int

class MCPDiscoveryResponse(BaseModel):
    server_id: str
    server_name: str
    status: str
    server_version: Optional[str] = None
    protocol_version: Optional[str] = "2024-11-05"
    total_tools: int
    total_resources: int
    total_prompts: int
    tools_added: int = 0
    tools_changed: int = 0
    resources_added: int = 0
    resources_changed: int = 0
    prompts_added: int = 0
    prompts_changed: int = 0
    stale_capabilities: int = 0
    reactivated_capabilities: int = 0
    unchanged_capabilities: int = 0
    discovered_at: str
    discovery_latency_ms: float

class MCPHealthCheckResponse(BaseModel):
    server_id: str
    server_name: str
    status: str
    is_healthy: bool
    latency_ms: Optional[float] = None
    last_health_check_at: str
    server_version: Optional[str] = None
    protocol_version: Optional[str] = None
    error: Optional[str] = None
