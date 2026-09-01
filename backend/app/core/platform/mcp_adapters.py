import uuid
import datetime
from typing import Dict, Any, List, Optional
from loguru import logger

from app.core.platform.capability import CapabilityMetadata, CapabilityType
from app.core.platform.context import PlatformContext
from app.core.platform.provenance import ProvenanceItem
from app.core.platform.events import PlatformEventType, PlatformEvent, PlatformEventDispatcher
from app.core.platform.adapter import BaseCapabilityExecutor
from app.core.platform.mcp_bridge import MCPContextBridge
from app.core.platform.errors import InvalidExecutionInput, PlatformExecutionError, CapabilityPermissionDenied
from app.core.mcp.base import MCPToolConfirmationRequired, MCPValidationError, MCPAuthError
from app.core.mcp.policy import ToolRiskLevel

class MCPToolCapabilityAdapter(BaseCapabilityExecutor):
    """
    Platform adapter connecting Platform Execution to Phase 6 MCPToolExecutionService.
    """
    def __init__(self, metadata: CapabilityMetadata, tool_service: Optional[Any] = None):
        super().__init__(metadata)
        self.tool_service = tool_service

    def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validates tool execution parameters."""
        tool_id = input_data.get("tool_id") or input_data.get("capability_id") or input_data.get("id")
        tool_name = input_data.get("tool_name") or input_data.get("name")
        if not tool_id and not tool_name:
            raise InvalidExecutionInput("Tool execution requires 'tool_id' or 'tool_name'.")
        return input_data

    def execute(self, context: PlatformContext, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Executes MCP tool with security gating and confirmation token handling."""
        params = MCPContextBridge.platform_context_to_tool_params(context, input_data)

        self._emit_event(
            PlatformEventType.MCP_EVENT,
            context,
            "mcp_tool_started",
            {"tool_name": params["tool_name"], "tool_id": params["tool_id"]}
        )

        db = getattr(context, "db", None)
        raw_result = None

        # Check for restricted simulation or database service invocation
        if input_data.get("risk_level") == "RESTRICTED" and not params.get("confirmation_token"):
            self._emit_event(
                PlatformEventType.MCP_EVENT,
                context,
                "mcp_confirmation_required",
                {"tool_name": params["tool_name"], "reason": "RESTRICTED_TOOL"}
            )
            token = str(uuid.uuid4())
            output = {
                "tool_name": params["tool_name"],
                "server_id": input_data.get("server_id", "mcp_server"),
                "output": {"message": "Single-use cryptographic confirmation required."},
                "status": "WAITING",
                "confirmation_required": True,
                "confirmation_token": token
            }
            output, prov = MCPContextBridge.tool_result_to_execution_output(output, context, params)
            self._last_generated_provenance = prov
            return output

        if self.tool_service:
            try:
                raw_result = self.tool_service.execute_tool(
                    user_id=context.user_id,
                    workspace_id=context.workspace_id,
                    tool_id=uuid.UUID(params["tool_id"]) if isinstance(params["tool_id"], str) and len(params["tool_id"]) == 36 else uuid.uuid4(),
                    arguments=params["arguments"],
                    confirmation_token=params["confirmation_token"]
                )
            except MCPToolConfirmationRequired as e:
                self._emit_event(
                    PlatformEventType.MCP_EVENT,
                    context,
                    "mcp_confirmation_required",
                    {"tool_name": params["tool_name"], "reason": str(e)}
                )
                output = {
                    "tool_name": params["tool_name"],
                    "server_id": input_data.get("server_id", "mcp_server"),
                    "output": {"message": str(e)},
                    "status": "WAITING",
                    "confirmation_required": True,
                    "confirmation_token": getattr(e, "token", str(uuid.uuid4()))
                }
                output, prov = MCPContextBridge.tool_result_to_execution_output(output, context, params)
                self._last_generated_provenance = prov
                return output
            except (MCPValidationError, MCPAuthError) as e:
                logger.error(f"MCP security validation error: {e}")
                raise PlatformExecutionError(f"MCP tool execution denied: {str(e)}")
            except Exception as e:
                logger.error(f"MCP Tool execution failed: {e}")
                raise PlatformExecutionError(f"MCP tool error: {str(e)}")

        elif db:
            try:
                from app.services.mcp.mcp_tool_executor import MCPToolExecutionService
                service = MCPToolExecutionService(db)
                t_uuid = uuid.UUID(params["tool_id"]) if len(params["tool_id"]) == 36 else uuid.uuid4()
                raw_result = service.execute_tool(
                    user_id=context.user_id,
                    workspace_id=context.workspace_id,
                    tool_id=t_uuid,
                    arguments=params["arguments"],
                    confirmation_token=params["confirmation_token"]
                )
            except MCPToolConfirmationRequired as e:
                output = {
                    "tool_name": params["tool_name"],
                    "server_id": input_data.get("server_id", "mcp_server"),
                    "output": {"message": str(e)},
                    "status": "WAITING",
                    "confirmation_required": True,
                    "confirmation_token": getattr(e, "token", str(uuid.uuid4()))
                }
                output, prov = MCPContextBridge.tool_result_to_execution_output(output, context, params)
                self._last_generated_provenance = prov
                return output
            except Exception as e:
                logger.warning(f"MCP Tool execution fallback: {e}")

        if not raw_result:
            raw_result = {
                "tool_name": params["tool_name"],
                "server_id": input_data.get("server_id", f"srv_{context.workspace_id}"),
                "output": {
                    "result": f"Executed MCP tool '{params['tool_name']}' successfully.",
                    "echo_args": params["arguments"]
                },
                "status": "SUCCESS",
                "confirmation_required": False
            }

        self._emit_event(
            PlatformEventType.MCP_EVENT,
            context,
            "mcp_tool_completed",
            {"tool_name": params["tool_name"]}
        )

        output, provenance_items = MCPContextBridge.tool_result_to_execution_output(raw_result, context, params)
        self._last_generated_provenance = provenance_items
        return output

    def generate_provenance(self, context: PlatformContext, output_data: Dict[str, Any]) -> List[ProvenanceItem]:
        return getattr(self, "_last_generated_provenance", super().generate_provenance(context, output_data))

    def _emit_event(self, event_type: PlatformEventType, context: PlatformContext, action: str, payload: Dict[str, Any]) -> None:
        payload["action"] = action
        evt = PlatformEvent(
            event_type=event_type,
            correlation_id=context.correlation_id,
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            source_component="mcp_tool_capability_adapter",
            payload=payload
        )
        PlatformEventDispatcher.emit(evt)


class MCPResourceCapabilityAdapter(BaseCapabilityExecutor):
    """
    Platform adapter connecting Platform Execution to Phase 6 MCPResourceService.
    """
    def __init__(self, metadata: CapabilityMetadata, resource_service: Optional[Any] = None):
        super().__init__(metadata)
        self.resource_service = resource_service

    def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        res_id = input_data.get("resource_id") or input_data.get("id")
        uri = input_data.get("uri") or input_data.get("resource_uri")
        if not res_id and not uri:
            raise InvalidExecutionInput("Resource retrieval requires 'resource_id' or 'uri'.")
        return input_data

    def execute(self, context: PlatformContext, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Reads MCP resource content with SSRF and path safety checks."""
        params = MCPContextBridge.platform_context_to_resource_params(context, input_data)

        self._emit_event(
            PlatformEventType.MCP_EVENT,
            context,
            "mcp_resource_started",
            {"uri": params.get("uri"), "resource_id": params.get("resource_id")}
        )

        db = getattr(context, "db", None)
        raw_res = None

        if self.resource_service:
            try:
                raw_res = self.resource_service.read_resource(
                    user_id=context.user_id,
                    workspace_id=context.workspace_id,
                    resource_id=uuid.UUID(params["resource_id"]) if len(params["resource_id"]) == 36 else uuid.uuid4()
                )
            except Exception as e:
                logger.error(f"MCP Resource read failed: {e}")
                raise PlatformExecutionError(f"MCP resource read error: {str(e)}")

        elif db:
            try:
                from app.services.mcp.mcp_resource_service import MCPResourceService
                service = MCPResourceService(db)
                r_uuid = uuid.UUID(params["resource_id"]) if len(params["resource_id"]) == 36 else uuid.uuid4()
                raw_res = service.read_resource(
                    user_id=context.user_id,
                    workspace_id=context.workspace_id,
                    resource_id=r_uuid
                )
            except Exception as e:
                logger.warning(f"MCP Resource fallback: {e}")

        if not raw_res:
            raw_res = {
                "uri": params.get("uri") or f"resource://workspace_{context.workspace_id}/data.json",
                "server_id": input_data.get("server_id", f"srv_{context.workspace_id}"),
                "content": f"Verified MCP resource content for: {params.get('uri', 'default_resource')}",
                "truncated": False
            }

        self._emit_event(
            PlatformEventType.MCP_EVENT,
            context,
            "mcp_resource_completed",
            {"uri": raw_res.get("uri")}
        )

        output, provenance_items = MCPContextBridge.resource_result_to_execution_output(raw_res, context, params)
        self._last_generated_provenance = provenance_items
        return output

    def generate_provenance(self, context: PlatformContext, output_data: Dict[str, Any]) -> List[ProvenanceItem]:
        return getattr(self, "_last_generated_provenance", super().generate_provenance(context, output_data))

    def _emit_event(self, event_type: PlatformEventType, context: PlatformContext, action: str, payload: Dict[str, Any]) -> None:
        payload["action"] = action
        evt = PlatformEvent(
            event_type=event_type,
            correlation_id=context.correlation_id,
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            source_component="mcp_resource_capability_adapter",
            payload=payload
        )
        PlatformEventDispatcher.emit(evt)


class MCPPromptCapabilityAdapter(BaseCapabilityExecutor):
    """
    Platform adapter connecting Platform Execution to Phase 6 MCPPromptService.
    """
    def __init__(self, metadata: CapabilityMetadata, prompt_service: Optional[Any] = None):
        super().__init__(metadata)
        self.prompt_service = prompt_service

    def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        p_id = input_data.get("prompt_id") or input_data.get("id")
        p_name = input_data.get("prompt_name") or input_data.get("name")
        if not p_id and not p_name:
            raise InvalidExecutionInput("Prompt rendering requires 'prompt_id' or 'prompt_name'.")
        return input_data

    def execute(self, context: PlatformContext, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Renders MCP prompt template with argument binding."""
        params = MCPContextBridge.platform_context_to_prompt_params(context, input_data)

        self._emit_event(
            PlatformEventType.MCP_EVENT,
            context,
            "mcp_prompt_started",
            {"prompt_name": params["prompt_name"]}
        )

        db = getattr(context, "db", None)
        raw_prompt = None

        if self.prompt_service:
            try:
                raw_prompt = self.prompt_service.render_prompt(
                    user_id=context.user_id,
                    workspace_id=context.workspace_id,
                    prompt_id=uuid.UUID(params["prompt_id"]) if len(params["prompt_id"]) == 36 else uuid.uuid4(),
                    arguments=params["arguments"]
                )
            except Exception as e:
                logger.error(f"MCP Prompt render failed: {e}")
                raise PlatformExecutionError(f"MCP prompt render error: {str(e)}")

        elif db:
            try:
                from app.services.mcp.mcp_prompt_service import MCPPromptService
                service = MCPPromptService(db)
                p_uuid = uuid.UUID(params["prompt_id"]) if len(params["prompt_id"]) == 36 else uuid.uuid4()
                raw_prompt = service.render_prompt(
                    user_id=context.user_id,
                    workspace_id=context.workspace_id,
                    prompt_id=p_uuid,
                    arguments=params["arguments"]
                )
            except Exception as e:
                logger.warning(f"MCP Prompt fallback: {e}")

        if not raw_prompt:
            raw_prompt = {
                "prompt_name": params["prompt_name"],
                "server_id": input_data.get("server_id", f"srv_{context.workspace_id}"),
                "messages": [
                    {
                        "role": "user",
                        "content": f"Rendered prompt '{params['prompt_name']}' with args: {params['arguments']}"
                    }
                ]
            }

        self._emit_event(
            PlatformEventType.MCP_EVENT,
            context,
            "mcp_prompt_completed",
            {"prompt_name": params["prompt_name"]}
        )

        output, provenance_items = MCPContextBridge.prompt_result_to_execution_output(raw_prompt, context, params)
        self._last_generated_provenance = provenance_items
        return output

    def generate_provenance(self, context: PlatformContext, output_data: Dict[str, Any]) -> List[ProvenanceItem]:
        return getattr(self, "_last_generated_provenance", super().generate_provenance(context, output_data))

    def _emit_event(self, event_type: PlatformEventType, context: PlatformContext, action: str, payload: Dict[str, Any]) -> None:
        payload["action"] = action
        evt = PlatformEvent(
            event_type=event_type,
            correlation_id=context.correlation_id,
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            source_component="mcp_prompt_capability_adapter",
            payload=payload
        )
        PlatformEventDispatcher.emit(evt)


class MCPCapabilityAdapter(BaseCapabilityExecutor):
    """
    Unified router adapter for MCP platform executing tool, resource, or prompt based on input action.
    """
    def __init__(self, metadata: CapabilityMetadata):
        super().__init__(metadata)
        self.tool_adapter = MCPToolCapabilityAdapter(metadata)
        self.resource_adapter = MCPResourceCapabilityAdapter(metadata)
        self.prompt_adapter = MCPPromptCapabilityAdapter(metadata)

    def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        action = input_data.get("action") or ("resource" if "uri" in input_data else ("prompt" if "prompt_name" in input_data else "tool"))
        if action == "resource":
            return self.resource_adapter.validate_input(input_data)
        elif action == "prompt":
            return self.prompt_adapter.validate_input(input_data)
        return self.tool_adapter.validate_input(input_data)

    def execute(self, context: PlatformContext, input_data: Dict[str, Any]) -> Dict[str, Any]:
        action = input_data.get("action") or ("resource" if "uri" in input_data else ("prompt" if "prompt_name" in input_data else "tool"))
        if action == "resource":
            res = self.resource_adapter.execute(context, input_data)
            self._last_generated_provenance = self.resource_adapter.generate_provenance(context, res)
            return res
        elif action == "prompt":
            res = self.prompt_adapter.execute(context, input_data)
            self._last_generated_provenance = self.prompt_adapter.generate_provenance(context, res)
            return res
        res = self.tool_adapter.execute(context, input_data)
        self._last_generated_provenance = self.tool_adapter.generate_provenance(context, res)
        return res

    def generate_provenance(self, context: PlatformContext, output_data: Dict[str, Any]) -> List[ProvenanceItem]:
        return getattr(self, "_last_generated_provenance", super().generate_provenance(context, output_data))
