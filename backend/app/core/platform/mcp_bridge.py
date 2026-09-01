import uuid
import datetime
from typing import Dict, Any, List, Tuple, Optional
from loguru import logger

from app.core.platform.context import PlatformContext
from app.core.platform.provenance import (
    ProvenanceItem,
    ProvenanceSourceType,
    ProvenanceTrustLevel
)
from app.core.mcp.security import CredentialStore
from app.core.platform.errors import InvalidExecutionInput

MAX_TOOL_ARG_DEPTH = 5
MAX_RESOURCE_URI_LENGTH = 1024
MAX_PROMPT_NAME_LENGTH = 256

class MCPContextBridge:
    """
    Bidirectional context bridge between PlatformContext and Phase 6 MCP Platform.
    Guarantees immutable caller and tenant identity, enforces argument bounds,
    sanitizes secrets, and generates UNTRUSTED_MCP provenance.
    """
    @staticmethod
    def platform_context_to_tool_params(
        context: PlatformContext,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validates, sanitizes, and binds MCP tool execution parameters.
        Guarantees tenant isolation: input_data cannot override workspace_id or user_id.
        """
        tool_id = input_data.get("tool_id") or input_data.get("capability_id") or input_data.get("id")
        tool_name = input_data.get("tool_name") or input_data.get("name") or str(tool_id or "")

        if not tool_id and not tool_name:
            raise InvalidExecutionInput("Tool execution requires 'tool_id' or 'tool_name'.")

        arguments = input_data.get("arguments") or input_data.get("args") or {}
        if not isinstance(arguments, dict):
            raise InvalidExecutionInput("Tool 'arguments' must be a JSON dictionary.")

        confirmation_token = input_data.get("confirmation_token")

        return {
            "tool_id": str(tool_id) if tool_id else str(uuid.uuid4()),
            "tool_name": str(tool_name),
            "arguments": CredentialStore.redact_sensitive_dict(dict(arguments)),
            "confirmation_token": str(confirmation_token) if confirmation_token else None,
            "workspace_id": context.workspace_id,
            "user_id": context.user_id,
            "timeout_seconds": input_data.get("timeout_seconds", 30)
        }

    @staticmethod
    def platform_context_to_resource_params(
        context: PlatformContext,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validates and binds MCP resource retrieval parameters with URI validation.
        """
        resource_id = input_data.get("resource_id") or input_data.get("id")
        uri = input_data.get("uri") or input_data.get("resource_uri")

        if not resource_id and not uri:
            raise InvalidExecutionInput("Resource retrieval requires 'resource_id' or 'uri'.")

        if uri:
            uri_str = str(uri).strip()
            if len(uri_str) > MAX_RESOURCE_URI_LENGTH:
                raise InvalidExecutionInput(f"Resource URI exceeds maximum length of {MAX_RESOURCE_URI_LENGTH} characters.")
            if uri_str.startswith("file://") or "localhost" in uri_str or "127.0.0.1" in uri_str:
                raise InvalidExecutionInput("Forbidden resource URI scheme or host.")

        return {
            "resource_id": str(resource_id) if resource_id else str(uuid.uuid4()),
            "uri": str(uri) if uri else None,
            "workspace_id": context.workspace_id,
            "user_id": context.user_id,
            "max_bytes": input_data.get("max_bytes", 1024 * 1024)
        }

    @staticmethod
    def platform_context_to_prompt_params(
        context: PlatformContext,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validates and binds MCP prompt rendering parameters.
        """
        prompt_id = input_data.get("prompt_id") or input_data.get("id")
        prompt_name = input_data.get("prompt_name") or input_data.get("name") or str(prompt_id or "")

        if not prompt_id and not prompt_name:
            raise InvalidExecutionInput("Prompt rendering requires 'prompt_id' or 'prompt_name'.")

        arguments = input_data.get("arguments") or input_data.get("args") or {}
        if not isinstance(arguments, dict):
            raise InvalidExecutionInput("Prompt 'arguments' must be a JSON dictionary.")

        return {
            "prompt_id": str(prompt_id) if prompt_id else str(uuid.uuid4()),
            "prompt_name": str(prompt_name),
            "arguments": CredentialStore.redact_sensitive_dict(dict(arguments)),
            "workspace_id": context.workspace_id,
            "user_id": context.user_id
        }

    @staticmethod
    def tool_result_to_execution_output(
        result: Any,
        context: PlatformContext,
        tool_info: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[ProvenanceItem]]:
        """
        Converts MCP tool execution result into structured platform output and UNTRUSTED_MCP provenance.
        """
        provenance_items: List[ProvenanceItem] = []

        if isinstance(result, dict):
            raw_output = result.get("output") or result.get("result") or {}
            server_id = result.get("server_id") or tool_info.get("server_id", "mcp_server")
            tool_name = result.get("tool_name") or tool_info.get("tool_name", "mcp_tool")
            status = result.get("status", "SUCCESS")
            is_conf_req = bool(result.get("confirmation_required", False))
            conf_token = result.get("confirmation_token")
        else:
            raw_output = getattr(result, "output", getattr(result, "content", {}))
            server_id = getattr(result, "server_id", tool_info.get("server_id", "mcp_server"))
            tool_name = getattr(result, "tool_name", tool_info.get("tool_name", "mcp_tool"))
            status = getattr(result, "status", "SUCCESS")
            is_conf_req = bool(getattr(result, "confirmation_required", False))
            conf_token = getattr(result, "confirmation_token", None)

        sanitized_output = CredentialStore.redact_sensitive_dict(
            raw_output if isinstance(raw_output, dict) else {"content": str(raw_output)}
        )

        # UNTRUSTED_MCP Provenance Item
        provenance_items.append(
            ProvenanceItem(
                source_type=ProvenanceSourceType.MCP_TOOL,
                source_id=str(tool_info.get("tool_id", "mcp_tool")),
                title=f"MCP Tool: {tool_name}",
                snippet=str(sanitized_output)[:500],
                trust_level=ProvenanceTrustLevel.UNTRUSTED_MCP,
                confidence=0.85,
                workspace_id=context.workspace_id,
                metadata={
                    "server_id": str(server_id),
                    "tool_name": str(tool_name),
                    "execution_status": str(status)
                }
            )
        )

        output = {
            "tool": str(tool_name),
            "tool_name": str(tool_name),
            "server_id": str(server_id),
            "output": sanitized_output,
            "result": sanitized_output,
            "status": str(status),
            "confirmation_required": is_conf_req,
            "confirmation_token": conf_token
        }
        return output, provenance_items

    @staticmethod
    def resource_result_to_execution_output(
        result: Any,
        context: PlatformContext,
        resource_info: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[ProvenanceItem]]:
        """
        Converts MCP resource reading result into structured output and UNTRUSTED_MCP provenance.
        """
        provenance_items: List[ProvenanceItem] = []

        if isinstance(result, dict):
            raw_content = result.get("content") or result.get("text") or ""
            uri = result.get("uri") or resource_info.get("uri", "resource://mcp")
            server_id = result.get("server_id") or resource_info.get("server_id", "mcp_server")
            truncated = bool(result.get("truncated", False))
        else:
            raw_content = getattr(result, "content", getattr(result, "text", ""))
            uri = getattr(result, "uri", resource_info.get("uri", "resource://mcp"))
            server_id = getattr(result, "server_id", resource_info.get("server_id", "mcp_server"))
            truncated = bool(getattr(result, "truncated", False))

        sanitized_content = CredentialStore.redact_sensitive_str(str(raw_content))

        provenance_items.append(
            ProvenanceItem(
                source_type=ProvenanceSourceType.MCP_RESOURCE,
                source_id=str(resource_info.get("resource_id", "mcp_resource")),
                title=f"MCP Resource: {uri}",
                snippet=sanitized_content[:500],
                trust_level=ProvenanceTrustLevel.UNTRUSTED_MCP,
                confidence=0.80,
                workspace_id=context.workspace_id,
                metadata={"server_id": str(server_id), "uri": str(uri)}
            )
        )

        output = {
            "resource_uri": str(uri),
            "server_id": str(server_id),
            "content": sanitized_content,
            "truncated": truncated,
            "status": "SUCCESS"
        }
        return output, provenance_items

    @staticmethod
    def prompt_result_to_execution_output(
        result: Any,
        context: PlatformContext,
        prompt_info: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[ProvenanceItem]]:
        """
        Converts MCP prompt render result into structured output and UNTRUSTED_MCP provenance.
        """
        provenance_items: List[ProvenanceItem] = []

        if isinstance(result, dict):
            messages = result.get("messages") or [{"role": "user", "content": result.get("text", "")}]
            prompt_name = result.get("prompt_name") or prompt_info.get("prompt_name", "mcp_prompt")
            server_id = result.get("server_id") or prompt_info.get("server_id", "mcp_server")
        else:
            messages = getattr(result, "messages", [{"role": "user", "content": getattr(result, "text", "")}])
            prompt_name = getattr(result, "prompt_name", prompt_info.get("prompt_name", "mcp_prompt"))
            server_id = getattr(result, "server_id", prompt_info.get("server_id", "mcp_server"))

        sanitized_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                sanitized_messages.append({
                    "role": str(msg.get("role", "user")),
                    "content": CredentialStore.redact_sensitive_str(str(msg.get("content", "")))
                })
            else:
                sanitized_messages.append({
                    "role": getattr(msg, "role", "user"),
                    "content": CredentialStore.redact_sensitive_str(str(getattr(msg, "content", "")))
                })

        provenance_items.append(
            ProvenanceItem(
                source_type=ProvenanceSourceType.MCP_PROMPT,
                source_id=str(prompt_info.get("prompt_id", "mcp_prompt")),
                title=f"MCP Prompt: {prompt_name}",
                snippet=str(sanitized_messages[0]["content"] if sanitized_messages else "")[:500],
                trust_level=ProvenanceTrustLevel.UNTRUSTED_MCP,
                confidence=0.85,
                workspace_id=context.workspace_id,
                metadata={"server_id": str(server_id), "prompt_name": str(prompt_name)}
            )
        )

        output = {
            "prompt_name": str(prompt_name),
            "server_id": str(server_id),
            "messages": sanitized_messages,
            "status": "SUCCESS"
        }
        return output, provenance_items
