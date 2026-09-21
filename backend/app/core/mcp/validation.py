import re
import json
import ipaddress
from urllib.parse import urlparse
from typing import Dict, Any, Optional, List
from app.core.mcp.base import MCPValidationError
from app.models.mcp import MCPTransport, MCPAuthenticationType

# Security constants
import os
from pathlib import Path

# Security constants
MAX_SERVER_NAME_LENGTH = 100
MAX_SERVER_URL_LENGTH = 512
MAX_METADATA_BYTES = 64 * 1024       # 64 KB
MAX_SCHEMA_BYTES = 32 * 1024         # 32 KB
MAX_PROMPT_ARGS_BYTES = 32 * 1024    # 32 KB
MAX_SCHEMA_DEPTH = 6

ALLOWED_URL_SCHEMES = {"http", "https", "stdio", "ws", "wss", "mock"}
ALLOWED_RESOURCE_SCHEMES = {"workspace", "db", "s3", "mock", "repo", "http", "https", "custom"}
DANGEROUS_URL_CHARACTERS = re.compile(r"[`$;|&><\n\r\t]")
VALID_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.\s]{1,100}$")

PROHIBITED_SSRF_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "169.254.169.254",
    "::1",
    "metadata.google.internal",
    "100.100.100.200",
}

class MCPValidator:
    """
    Strict validation utility for MCP server configurations, URLs, resource URIs, prompt schemas, and filesystem paths.
    """
    @staticmethod
    def is_safe_ip(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """
        Determines if an IP address is a safe public routable destination.
        Rejects loopback, private, link-local, reserved, multicast, and cloud metadata.
        """
        if ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_link_local or ip_obj.is_reserved or ip_obj.is_multicast or ip_obj.is_unspecified:
            return False
        # Specific cloud metadata checks
        if str(ip_obj) in {"169.254.169.254", "100.100.100.200"}:
            return False
        # Check IPv4-mapped IPv6
        if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped:
            return MCPValidator.is_safe_ip(ip_obj.ipv4_mapped)
        return True

    @staticmethod
    def parse_and_validate_ip(host_str: str) -> Optional[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        """
        Attempts to parse an IP literal across standard, decimal, hex, and octal notations.
        """
        clean_host = host_str.strip("[]")
        # Standard IP parse
        try:
            return ipaddress.ip_address(clean_host)
        except ValueError:
            pass

        # Hex / Decimal / Octal integer IP formats (e.g., 2130706433, 0x7f000001)
        try:
            if clean_host.startswith("0x") or clean_host.startswith("0X"):
                int_val = int(clean_host, 16)
                if 0 <= int_val <= 0xFFFFFFFF:
                    return ipaddress.IPv4Address(int_val)
            elif clean_host.isdigit():
                int_val = int(clean_host, 10)
                if 0 <= int_val <= 0xFFFFFFFF:
                    return ipaddress.IPv4Address(int_val)
        except Exception:
            pass

        return None

    @staticmethod
    def validate_safe_url(url: str, allowed_schemes: Optional[set] = None) -> tuple[bool, str]:
        """
        Comprehensive SSRF and URL structure validator.
        """
        if not url or not isinstance(url, str):
            return False, "URL cannot be empty."
        clean_url = url.strip()
        if len(clean_url) > MAX_SERVER_URL_LENGTH:
            return False, f"URL exceeds maximum allowed length of {MAX_SERVER_URL_LENGTH} characters."
        if DANGEROUS_URL_CHARACTERS.search(clean_url):
            return False, "URL contains prohibited characters or command injection signatures."

        schemes = allowed_schemes or {"http", "https", "ws", "wss"}
        try:
            parsed = urlparse(clean_url)
            scheme = (parsed.scheme or "").lower()
            if not scheme or scheme not in schemes:
                return False, f"URL scheme '{scheme}' is forbidden. Allowed schemes: {', '.join(schemes)}."

            if parsed.username or parsed.password:
                return False, "URL contains forbidden embedded credentials."

            hostname = (parsed.hostname or "").lower()
            if not hostname:
                return False, "URL is missing a valid hostname or destination."

            if hostname in PROHIBITED_SSRF_HOSTS:
                return False, f"Destination hostname '{hostname}' is prohibited by SSRF policy."

            ip_obj = MCPValidator.parse_and_validate_ip(hostname)
            if ip_obj is not None:
                if not MCPValidator.is_safe_ip(ip_obj):
                    return False, f"IP address destination '{ip_obj}' is private/internal and prohibited by SSRF policy."

            return True, "URL is valid and safe."
        except Exception as e:
            return False, f"Malformed URL: {e}"

    @staticmethod
    def validate_safe_path(base_dir: str | Path, target_path: str) -> Path:
        """
        Validates that target_path resolves strictly within base_dir, preventing path traversal attacks.
        """
        if not target_path or "\x00" in target_path:
            raise MCPValidationError("Invalid filesystem path: empty or contains null bytes.")
        
        base = Path(base_dir).resolve()
        # Combine and resolve
        resolved = (base / target_path).resolve()
        
        try:
            if not resolved.is_relative_to(base):
                raise MCPValidationError(f"Path traversal detected: '{target_path}' escapes base directory '{base}'.")
        except AttributeError:
            # Fallback for Python < 3.9 if ever run
            if not str(resolved).startswith(str(base)):
                raise MCPValidationError(f"Path traversal detected: '{target_path}' escapes base directory '{base}'.")

        return resolved

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
    def validate_resource_uri(uri: str) -> str:
        """
        Validates resource URIs, preventing path traversal, local filesystem scheme access,
        embedded credentials, and internal network SSRF attempts.
        """
        if not uri or not uri.strip():
            raise MCPValidationError("Resource URI cannot be empty.")
        clean_uri = uri.strip()

        # 1. Path traversal checks
        if ".." in clean_uri or clean_uri.startswith("/") or clean_uri.startswith("\\"):
            raise MCPValidationError("Resource URI contains illegal path traversal characters ('..', absolute root path).")

        # 2. Reject file:// scheme outright
        if clean_uri.lower().startswith("file://") or clean_uri.lower().startswith("file:\\"):
            raise MCPValidationError("Local filesystem 'file://' URI scheme is strictly forbidden.")

        try:
            parsed = urlparse(clean_uri)
            scheme = parsed.scheme.lower()
            if not scheme:
                raise MCPValidationError("Resource URI must include a valid URI scheme (e.g. 'workspace://', 'db://', 'https://').")

            if scheme not in ALLOWED_RESOURCE_SCHEMES:
                raise MCPValidationError(f"Unsupported resource URI scheme '{scheme}'. Allowed: {', '.join(ALLOWED_RESOURCE_SCHEMES)}")

            if parsed.username or parsed.password:
                raise MCPValidationError("Resource URI cannot contain embedded credentials.")

            if scheme in ("http", "https"):
                is_safe, reason = MCPValidator.validate_safe_url(clean_uri, allowed_schemes={"http", "https"})
                if not is_safe:
                    raise MCPValidationError(reason)

        except MCPValidationError:
            raise
        except Exception as e:
            raise MCPValidationError(f"Malformed resource URI: {e}")

        return clean_uri

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

        # Enforce max 50 properties limit
        props = schema.get("properties", {})
        if isinstance(props, dict) and len(props) > 50:
            raise MCPValidationError(f"Tool input schema defines {len(props)} properties, exceeding maximum limit of 50.")

        return schema

    @staticmethod
    def validate_prompt_arguments(
        arguments: Optional[Dict[str, Any]],
        prompt_def_arguments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Validates prompt arguments dictionary against prompt template definition.
        """
        if arguments is None:
            arguments = {}

        if not isinstance(arguments, dict):
            raise MCPValidationError("Prompt arguments must be a JSON object dictionary.")

        try:
            serialized = json.dumps(arguments)
            if len(serialized.encode("utf-8")) > MAX_PROMPT_ARGS_BYTES:
                raise MCPValidationError(f"Prompt arguments exceed maximum payload size of {MAX_PROMPT_ARGS_BYTES} bytes.")
        except Exception as e:
            raise MCPValidationError(f"Prompt arguments are not valid JSON: {e}")

        if prompt_def_arguments:
            for arg_def in prompt_def_arguments:
                arg_name = arg_def.get("name")
                is_req = arg_def.get("required", False)
                if is_req and (arg_name not in arguments or arguments[arg_name] is None):
                    raise MCPValidationError(f"Missing required prompt argument: '{arg_name}'.")

        return arguments
