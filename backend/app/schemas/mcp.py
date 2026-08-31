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
    last_connected_at: Optional[datetime.datetime] = None
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
    protocol_version: str
    total_tools: int
    total_resources: int
    total_prompts: int
    added_capabilities: int
    updated_capabilities: int
    pruned_capabilities: int
    discovery_latency_ms: float
