import uuid
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field

class JSONRPCRequest(BaseModel):
    """Standard JSON-RPC 2.0 Request Envelope for MCP communication."""
    jsonrpc: str = "2.0"
    id: Union[str, int] = Field(default_factory=lambda: str(uuid.uuid4()))
    method: str
    params: Optional[Dict[str, Any]] = None

class JSONRPCResponse(BaseModel):
    """Standard JSON-RPC 2.0 Response Envelope for MCP communication."""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

class MCPProtocolMethods:
    """Standard method names per the Model Context Protocol Specification."""
    INITIALIZE = "initialize"
    PING = "ping"
    TOOLS_LIST = "tools/list"
    RESOURCES_LIST = "resources/list"
    PROMPTS_LIST = "prompts/list"
    TOOLS_CALL = "tools/call"
    RESOURCES_READ = "resources/read"
    PROMPTS_GET = "prompts/get"

class MCPErrorCodes:
    """Standard JSON-RPC & MCP protocol error codes."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    UNAUTHORIZED = -32001
    CONNECTION_FAILED = -32002
    TIMEOUT = -32003
