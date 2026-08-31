import re
import json
from urllib.parse import urlparse
from typing import Dict, Any, Optional
from app.core.mcp.base import MCPValidationError
from app.models.mcp import MCPTransport, MCPAuthenticationType

# Security constants
MAX_SERVER_NAME_LENGTH = 100
MAX_SERVER_URL_LENGTH = 512
MAX_METADATA_BYTES = 64 * 1024       # 64 KB
MAX_SCHEMA_BYTES = 32 * 1024         # 32 KB
MAX_SCHEMA_DEPTH = 6

ALLOWED_URL_SCHEMES = {"http", "https", "stdio", "ws", "wss", "mock"}
DANGEROUS_URL_CHARACTERS = re.compile(r"[`$;|&><\n\r\t]")
VALID_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.\s]{1,100}$")

class MCPValidator:
    """
    Strict validation utility for MCP server configurations, URLs, and capability schemas.
    """
    @staticmethod
    def validate_server_name(name: str) -> str:
        if not name or not name.strip():
            raise MCPValidationError("MCP server name cannot be empty.")
        clean_name = name.strip()
        if len(clean_name) > MAX_SERVER_NAME_LENGTH:
            raise MCPValidationError(f"MCP server name exceeds maximum length of {MAX_SERVER_NAME_LENGTH} characters.")
        if not VALID_NAME_PATTERN.match(clean_name):
            raise MCPValidationError("MCP server name contains invalid characters. Allowed: alphanumeric, hyphens, underscores, dots, and spaces.")
        return clean_name

    @staticmethod
    def validate_server_url(url: str, transport: MCPTransport = MCPTransport.SSE) -> str:
        if not url or not url.strip():
            raise MCPValidationError("MCP server URL cannot be empty.")
        clean_url = url.strip()
        if len(clean_url) > MAX_SERVER_URL_LENGTH:
            raise MCPValidationError(f"MCP server URL exceeds maximum length of {MAX_SERVER_URL_LENGTH} characters.")
        
        # Check for command injection or dangerous characters
        if DANGEROUS_URL_CHARACTERS.search(clean_url):
            raise MCPValidationError("MCP server URL contains prohibited shell/command injection characters.")

        if transport == MCPTransport.STDIO:
            # For stdio, URL represents an executable command / script path
            if clean_url.startswith("http://") or clean_url.startswith("https://"):
                raise MCPValidationError("STDIO transport cannot use HTTP/HTTPS URLs.")
            return clean_url

        try:
            parsed = urlparse(clean_url)
            if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
                raise MCPValidationError(f"Unsupported URL scheme '{parsed.scheme}'. Allowed schemes: {', '.join(ALLOWED_URL_SCHEMES)}.")
            if not parsed.netloc and transport != MCPTransport.STDIO:
                raise MCPValidationError("Invalid server URL: missing host or network location.")
        except MCPValidationError:
            raise
        except Exception as e:
            raise MCPValidationError(f"Malformed server URL: {e}")

        return clean_url

    @staticmethod
    def validate_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if metadata is None:
            return {}
        try:
            serialized = json.dumps(metadata)
            if len(serialized.encode("utf-8")) > MAX_METADATA_BYTES:
                raise MCPValidationError(f"Metadata payload exceeds maximum size limit of {MAX_METADATA_BYTES} bytes.")
        except (TypeError, ValueError) as e:
            raise MCPValidationError(f"Metadata must be JSON serializable: {e}")
        return metadata

    @staticmethod
    def validate_tool_input_schema(schema: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validates JSON Schema definitions for discovered MCP tools.
        Ensures safe types and bounded depth to prevent recursive parsing attacks.
        """
        if schema is None or not schema:
            return {"type": "object", "properties": {}}

        if not isinstance(schema, dict):
            raise MCPValidationError("Tool input schema must be a JSON object dictionary.")

        try:
            serialized = json.dumps(schema)
            if len(serialized.encode("utf-8")) > MAX_SCHEMA_BYTES:
                raise MCPValidationError(f"Tool input schema exceeds maximum size limit of {MAX_SCHEMA_BYTES} bytes.")
        except Exception as e:
            raise MCPValidationError(f"Tool input schema is not valid JSON: {e}")

        def check_depth(obj: Any, current_depth: int = 1):
            if current_depth > MAX_SCHEMA_DEPTH:
                raise MCPValidationError(f"Tool input schema exceeds maximum nesting depth of {MAX_SCHEMA_DEPTH}.")
            if isinstance(obj, dict):
                for k, v in obj.items():
                    check_depth(v, current_depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    check_depth(item, current_depth + 1)

        check_depth(schema)

        # Standardize default schema type if missing
        if "type" not in schema:
            schema["type"] = "object"

        return schema
