import abc
import enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.models.mcp import MCPTransport, MCPServerStatus, MCPCapabilityType, MCPAuthenticationType

class MCPClientError(Exception):
    """Base exception for all MCP client failures."""
    pass

class MCPConnectionError(MCPClientError):
    """Raised when unable to connect to target MCP server."""
    pass

class MCPValidationError(MCPClientError):
    """Raised when an MCP payload, URL, or schema is invalid."""
    pass

class MCPAuthError(MCPClientError):
    """Raised when MCP server authentication fails."""
    pass

class MCPTimeoutError(MCPClientError):
    """Raised when an MCP operation times out."""
    pass

class MCPToolConfirmationRequired(MCPClientError):
    """Raised when a tool is RESTRICTED and requires user confirmation."""
    def __init__(self, message: str, tool_id: str, risk_reasons: List[str]):
        super().__init__(message)
        self.tool_id = tool_id
        self.risk_reasons = risk_reasons

class MCPToolDefinition(BaseModel):
    """Represents a discovered MCP tool capability."""
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    meta_data: Dict[str, Any] = Field(default_factory=dict)

class MCPResourceDefinition(BaseModel):
    """Represents a discovered MCP resource capability."""
    uri: str = Field(..., max_length=512)
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    mime_type: Optional[str] = None
    meta_data: Dict[str, Any] = Field(default_factory=dict)

class MCPPromptDefinition(BaseModel):
    """Represents a discovered MCP prompt template capability."""
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    arguments: List[Dict[str, Any]] = Field(default_factory=list)
    meta_data: Dict[str, Any] = Field(default_factory=dict)

class MCPInitializeResult(BaseModel):
    """Handshake result returned by MCP server initialize call."""
    protocol_version: str = "2024-11-05"
    server_name: str
    server_version: Optional[str] = None
    instructions: Optional[str] = None
    capabilities: Dict[str, Any] = Field(default_factory=dict)

class MCPPingResult(BaseModel):
    """Ping healthcheck response."""
    latency_ms: float
    status: str = "ok"

class MCPToolExecutionResult(BaseModel):
    """Standardized response from an MCP tool execution."""
    execution_id: str
    tool_id: str
    tool_name: str
    status: str  # SUCCESS, FAILED, TIMED_OUT, DENIED, REQUIRES_CONFIRMATION
    result: Dict[str, Any] = Field(default_factory=dict)
    text_content: Optional[str] = None
    duration_ms: float = 0.0
    retry_count: int = 0
    truncated: bool = False
    error: Optional[str] = None

class BaseMCPClient(abc.ABC):
    """
    Standard contract for communicating with any Model Context Protocol server.
    """
    def __init__(self, server_url: str, auth_config: Optional[Dict[str, Any]] = None, timeout: float = 10.0):
        self.server_url = server_url
        self.auth_config = auth_config or {}
        self.timeout = timeout
        self.is_connected = False

    @abc.abstractmethod
    async def initialize(self) -> MCPInitializeResult:
        """Performs protocol handshake and retrieves server metadata."""
        pass

    @abc.abstractmethod
    async def list_tools(self) -> List[MCPToolDefinition]:
        """Discovers all tools exposed by the MCP server."""
        pass

    @abc.abstractmethod
    async def list_resources(self) -> List[MCPResourceDefinition]:
        """Discovers all resources exposed by the MCP server."""
        pass

    @abc.abstractmethod
    async def list_prompts(self) -> List[MCPPromptDefinition]:
        """Discovers all prompt templates exposed by the MCP server."""
        pass

    @abc.abstractmethod
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a named tool on the MCP server and returns the structured output."""
        pass

    @abc.abstractmethod
    async def ping(self) -> MCPPingResult:
        """Pings server to measure connection latency and liveness."""
        pass

    @abc.abstractmethod
    async def close(self) -> None:
        """Closes any underlying transport connections."""
        pass
