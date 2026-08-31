import uuid
import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models.mcp import MCPTransport, MCPServerStatus, MCPCapabilityType, MCPAuthenticationType
from app.core.mcp.security import CredentialStore
from app.core.mcp.policy import ToolRiskLevel, ToolPolicyDecision

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

# ==========================================
# Phase 6.3 Tool Catalog Schemas
# ==========================================

class MCPToolResponse(BaseModel):
    id: uuid.UUID
    server_id: uuid.UUID
    server_name: str
    server_transport: str
    server_status: str
    server_enabled: bool
    name: str
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    enabled: bool
    is_stale: bool = False
    stale_at: Optional[datetime.datetime] = None
    definition_hash: Optional[str] = None
    version: int = 1
    risk_level: str
    policy_decision: str
    risk_reasons: List[str] = Field(default_factory=list)
    available_for_execution: bool
    first_discovered_at: Optional[datetime.datetime] = None
    last_discovered_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

class MCPToolListResponse(BaseModel):
    tools: List[MCPToolResponse]
    total: int

class MCPToolSearchRequest(BaseModel):
    query: str = Field(..., max_length=200, description="Search query matching tool name or description")
    server_id: Optional[uuid.UUID] = Field(None, description="Optional server ID filter")
    risk_level: Optional[ToolRiskLevel] = Field(None, description="Filter by risk category: safe, restricted, invalid")
    enabled_only: bool = Field(True, description="Filter for enabled tools")
    include_stale: bool = Field(False, description="Whether to include stale tools")
    limit: int = Field(20, ge=1, le=100, description="Maximum number of results")

class MCPToolSearchResponse(BaseModel):
    results: List[MCPToolResponse]
    total: int
    query: str

# ==========================================
# Phase 6.4 Tool Execution Schemas
# ==========================================

class MCPToolExecuteRequest(BaseModel):
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Execution arguments conforming to input_schema")
    confirmation_token: Optional[str] = Field(None, description="Single-use confirmation token for RESTRICTED tools")
    timeout: Optional[float] = Field(15.0, ge=1.0, le=60.0, description="Execution timeout in seconds")

class MCPToolExecutionResponse(BaseModel):
    execution_id: str
    tool_id: str
    tool_name: str
    status: str
    result: Dict[str, Any] = Field(default_factory=dict)
    text_content: Optional[str] = None
    duration_ms: float
    retry_count: int = 0
    truncated: bool = False
    error: Optional[str] = None

class MCPToolConfirmationRequest(BaseModel):
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments to bind to the confirmation token")

class MCPToolConfirmationResponse(BaseModel):
    token: str
    tool_id: str
    expires_in_seconds: int
    risk_level: str
    risk_reasons: List[str] = Field(default_factory=list)

# ==========================================
# Phase 6.5 Resource Schemas
# ==========================================

class MCPResourceResponse(BaseModel):
    id: uuid.UUID
    server_id: uuid.UUID
    server_name: str
    server_transport: str
    server_status: str
    server_enabled: bool
    name: str
    uri: str
    mime_type: Optional[str] = "text/plain"
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    enabled: bool
    is_stale: bool = False
    stale_at: Optional[datetime.datetime] = None
    definition_hash: Optional[str] = None
    version: int = 1
    first_discovered_at: Optional[datetime.datetime] = None
    last_discovered_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

class MCPResourceListResponse(BaseModel):
    resources: List[MCPResourceResponse]
    total: int

class MCPResourceSearchRequest(BaseModel):
    query: str = Field(..., max_length=200, description="Search query matching resource name or URI")
    server_id: Optional[uuid.UUID] = Field(None, description="Optional server ID filter")
    enabled_only: bool = Field(True, description="Filter for enabled resources")
    include_stale: bool = Field(False, description="Whether to include stale resources")
    limit: int = Field(20, ge=1, le=100)

class MCPResourceSearchResponse(BaseModel):
    results: List[MCPResourceResponse]
    total: int
    query: str

class MCPResourceReadResponse(BaseModel):
    uri: str
    mime_type: Optional[str] = "text/plain"
    text: Optional[str] = None
    size: int = 0
    truncated: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

# ==========================================
# Phase 6.5 Prompt Schemas
# ==========================================

class MCPPromptResponse(BaseModel):
    id: uuid.UUID
    server_id: uuid.UUID
    server_name: str
    server_transport: str
    server_status: str
    server_enabled: bool
    name: str
    description: Optional[str] = None
    arguments: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    enabled: bool
    is_stale: bool = False
    stale_at: Optional[datetime.datetime] = None
    definition_hash: Optional[str] = None
    version: int = 1
    first_discovered_at: Optional[datetime.datetime] = None
    last_discovered_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

class MCPPromptListResponse(BaseModel):
    prompts: List[MCPPromptResponse]
    total: int

class MCPPromptSearchRequest(BaseModel):
    query: str = Field(..., max_length=200, description="Search query matching prompt name or description")
    server_id: Optional[uuid.UUID] = Field(None, description="Optional server ID filter")
    enabled_only: bool = Field(True, description="Filter for enabled prompts")
    include_stale: bool = Field(False, description="Whether to include stale prompts")
    limit: int = Field(20, ge=1, le=100)

class MCPPromptSearchResponse(BaseModel):
    results: List[MCPPromptResponse]
    total: int
    query: str

class MCPPromptRenderRequest(BaseModel):
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments bound to the prompt template")

class MCPPromptMessageSchema(BaseModel):
    role: str = "user"
    content: str
    untrusted: bool = True

class MCPPromptRenderResponse(BaseModel):
    prompt_id: str
    name: str
    description: Optional[str] = None
    messages: List[MCPPromptMessageSchema] = Field(default_factory=list)
    untrusted: bool = True

# ==========================================
# Phase 6.6 Security & Permission Schemas
# ==========================================

class MCPSecurityStatusResponse(BaseModel):
    workspace_id: str
    user_id: str
    user_role: str
    policy_engine_active: bool
    trust_label_policy: str
    active_permissions: List[str]
    total_servers: int
    total_tools: int
    total_resources: int
    total_prompts: int
    confirmation_gate_active: bool
    ssrf_defense_active: bool

class MCPSecurityAuditEventSchema(BaseModel):
    id: str
    event_type: str
    user_id: str
    workspace_id: str
    server_id: Optional[str] = None
    capability_id: Optional[str] = None
    operation: str
    decision: str
    reason_code: str
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MCPSecurityAuditLogResponse(BaseModel):
    events: List[MCPSecurityAuditEventSchema]
    total: int


