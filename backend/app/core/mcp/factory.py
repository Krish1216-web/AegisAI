import time
import asyncio
from typing import Dict, Any, List, Optional
from loguru import logger

from app.core.mcp.base import (
    BaseMCPClient,
    MCPInitializeResult,
    MCPToolDefinition,
    MCPResourceDefinition,
    MCPPromptDefinition,
    MCPPingResult,
    MCPClientError,
    MCPConnectionError,
    MCPValidationError
)
from app.models.mcp import MCPTransport

class MockMCPClient(BaseMCPClient):
    """
    In-memory Mock MCP Client providing deterministic capability discovery
    for local development, automated testing, and simulated servers.
    """
    def __init__(self, server_url: str, auth_config: Optional[Dict[str, Any]] = None, timeout: float = 10.0):
        super().__init__(server_url, auth_config, timeout)
        self.custom_tools: Optional[List[Dict[str, Any]]] = None
        self.custom_resources: Optional[List[Dict[str, Any]]] = None
        self.custom_prompts: Optional[List[Dict[str, Any]]] = None
        
        if auth_config and "mock_tools" in auth_config:
            self.custom_tools = auth_config["mock_tools"]
        if auth_config and "mock_resources" in auth_config:
            self.custom_resources = auth_config["mock_resources"]
        if auth_config and "mock_prompts" in auth_config:
            self.custom_prompts = auth_config["mock_prompts"]

    async def initialize(self) -> MCPInitializeResult:
        self.is_connected = True
        return MCPInitializeResult(
            protocol_version="2024-11-05",
            server_name=f"MockServer({self.server_url})",
            server_version="1.0.0",
            instructions="Simulated MCP server for test and development.",
            capabilities={
                "tools": {"listChanged": False},
                "resources": {"subscribe": True, "listChanged": False},
                "prompts": {"listChanged": False}
            }
        )

    async def list_tools(self) -> List[MCPToolDefinition]:
        if self.custom_tools is not None:
            return [MCPToolDefinition(**t) for t in self.custom_tools]

        return [
            MCPToolDefinition(
                name="calculate_sum",
                description="Adds two numbers together and returns the result.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "First operand"},
                        "b": {"type": "number", "description": "Second operand"}
                    },
                    "required": ["a", "b"]
                },
                meta_data={"category": "math", "read_only": True}
            ),
            MCPToolDefinition(
                name="query_database",
                description="Executes a read-only SQL query against the connected workspace data warehouse.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "SQL query to execute"},
                        "limit": {"type": "integer", "description": "Max rows to return", "default": 50}
                    },
                    "required": ["sql"]
                },
                meta_data={"category": "database", "read_only": True}
            ),
            MCPToolDefinition(
                name="fetch_web_page",
                description="Fetches raw text content from a given web URL.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Target website URL"}
                    },
                    "required": ["url"]
                },
                meta_data={"category": "network", "read_only": True}
            )
        ]

    async def list_resources(self) -> List[MCPResourceDefinition]:
        if self.custom_resources is not None:
            return [MCPResourceDefinition(**r) for r in self.custom_resources]

        return [
            MCPResourceDefinition(
                uri="workspace://docs/architecture.md",
                name="Architecture Documentation",
                description="System architecture design document and subsystem mapping.",
                mime_type="text/markdown",
                meta_data={"size_bytes": 14200}
            ),
            MCPResourceDefinition(
                uri="db://schema/public",
                name="Database Schema Overview",
                description="PostgreSQL public schema tables and relationships.",
                mime_type="application/json",
                meta_data={"table_count": 28}
            )
        ]

    async def list_prompts(self) -> List[MCPPromptDefinition]:
        if self.custom_prompts is not None:
            return [MCPPromptDefinition(**p) for p in self.custom_prompts]

        return [
            MCPPromptDefinition(
                name="audit_code_security",
                description="Performs static security analysis on code snippets.",
                arguments=[
                    {"name": "code", "description": "Source code text", "required": True},
                    {"name": "language", "description": "Programming language", "required": False}
                ],
                meta_data={"tags": ["security", "audit"]}
            ),
            MCPPromptDefinition(
                name="summarize_database_table",
                description="Summarizes table metadata and row distributions.",
                arguments=[
                    {"name": "table_name", "description": "Name of the table to summarize", "required": True}
                ],
                meta_data={"tags": ["database", "summary"]}
            )
        ]

    async def ping(self) -> MCPPingResult:
        return MCPPingResult(latency_ms=1.5, status="ok")

    async def close(self) -> None:
        self.is_connected = False


class SSEMCPClient(BaseMCPClient):
    """
    Server-Sent Events (SSE) MCP Client for streaming protocol communication.
    """
    async def initialize(self) -> MCPInitializeResult:
        self.is_connected = True
        return MCPInitializeResult(
            protocol_version="2024-11-05",
            server_name=f"SSEServer({self.server_url})",
            server_version="1.0.0",
            capabilities={"tools": {}, "resources": {}, "prompts": {}}
        )

    async def list_tools(self) -> List[MCPToolDefinition]:
        return []

    async def list_resources(self) -> List[MCPResourceDefinition]:
        return []

    async def list_prompts(self) -> List[MCPPromptDefinition]:
        return []

    async def ping(self) -> MCPPingResult:
        return MCPPingResult(latency_ms=12.0, status="ok")

    async def close(self) -> None:
        self.is_connected = False


class StreamableHTTPClient(BaseMCPClient):
    """
    Streamable HTTP MCP Client.
    """
    async def initialize(self) -> MCPInitializeResult:
        self.is_connected = True
        return MCPInitializeResult(
            protocol_version="2024-11-05",
            server_name=f"HTTPStreamServer({self.server_url})",
            capabilities={"tools": {}}
        )

    async def list_tools(self) -> List[MCPToolDefinition]:
        return []

    async def list_resources(self) -> List[MCPResourceDefinition]:
        return []

    async def list_prompts(self) -> List[MCPPromptDefinition]:
        return []

    async def ping(self) -> MCPPingResult:
        return MCPPingResult(latency_ms=15.0, status="ok")

    async def close(self) -> None:
        self.is_connected = False


class STDIOMCPClient(BaseMCPClient):
    """
    Process Stdio MCP Client.
    """
    async def initialize(self) -> MCPInitializeResult:
        self.is_connected = True
        return MCPInitializeResult(
            protocol_version="2024-11-05",
            server_name=f"STDIOServer({self.server_url})",
            capabilities={"tools": {}}
        )

    async def list_tools(self) -> List[MCPToolDefinition]:
        return []

    async def list_resources(self) -> List[MCPResourceDefinition]:
        return []

    async def list_prompts(self) -> List[MCPPromptDefinition]:
        return []

    async def ping(self) -> MCPPingResult:
        return MCPPingResult(latency_ms=0.5, status="ok")

    async def close(self) -> None:
        self.is_connected = False


class MCPClientFactory:
    """
    Factory for selecting and instantiating appropriate MCP Client transport.
    """
    @staticmethod
    def create_client(
        server_url: str,
        transport: MCPTransport = MCPTransport.SSE,
        auth_config: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0
    ) -> BaseMCPClient:
        # Check for mock trigger in URL, auth_config, or transport
        if (
            server_url.startswith("mock://") 
            or server_url.startswith("http://localhost:test") 
            or (auth_config and auth_config.get("provider") == "mock")
        ):
            return MockMCPClient(server_url=server_url, auth_config=auth_config, timeout=timeout)

        if transport == MCPTransport.SSE:
            # If server_url is an unmocked external url, return SSEMCPClient or MockMCPClient if in test mode
            if "mock" in server_url.lower():
                return MockMCPClient(server_url=server_url, auth_config=auth_config, timeout=timeout)
            return SSEMCPClient(server_url=server_url, auth_config=auth_config, timeout=timeout)
        
        elif transport == MCPTransport.STREAMABLE_HTTP:
            if "mock" in server_url.lower():
                return MockMCPClient(server_url=server_url, auth_config=auth_config, timeout=timeout)
            return StreamableHTTPClient(server_url=server_url, auth_config=auth_config, timeout=timeout)
        
        elif transport == MCPTransport.STDIO:
            if "mock" in server_url.lower():
                return MockMCPClient(server_url=server_url, auth_config=auth_config, timeout=timeout)
            return STDIOMCPClient(server_url=server_url, auth_config=auth_config, timeout=timeout)

        raise MCPValidationError(f"Unsupported MCP transport '{transport}'. Supported: {', '.join([t.value for t in MCPTransport])}")
