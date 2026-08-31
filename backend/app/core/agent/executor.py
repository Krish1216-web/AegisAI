import time
import json
import uuid
import datetime
import hashlib
from typing import Dict, Any, Set, Optional
from loguru import logger

from app.core.agent.base import BaseAgent, AgentResult, ExecutionContext
from app.core.agent.state import AgentState, ExecutionStatus
from app.core.agent.exceptions import (
    ToolNotFound, ToolDisabled, ToolPermissionDenied, ToolArgumentValidationError,
    ToolExecutionError, ToolTimeout, ToolConfirmationRequired, ToolConfirmationInvalid,
    ToolAlreadyExecuted
)
from app.core.agent.tools import (
    ToolRegistry, ToolExecutionRequest, ToolExecutionResult, ToolExecutionStatus,
    generate_confirmation_token, MockCalculatorTool, MockSearchTool, MockDocumentReaderTool, MockWeatherTool
)

class ToolExecutorAgent(BaseAgent):
    """
    ToolExecutorAgent coordinates safe tool runs from planning steps across
    both local built-in tools and external Model Context Protocol (MCP) capabilities.
    """
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.executed_keys: Dict[str, ToolExecutionResult] = {}

    @property
    def name(self) -> str:
        return "ToolExecutorAgent"

    @property
    def description(self) -> str:
        return "Resolves and executes approved local and MCP tools in a secure isolated environment."

    def validate_input(self, state: AgentState) -> bool:
        # Require original prompt or active planner steps
        if not state.get("original_prompt") and "PlannerAgent" not in state.get("agent_outputs", {}):
            return False
        return True

    def validate_output(self, result: AgentResult) -> bool:
        if not result.output:
            return False
        return True

    def health_check(self) -> bool:
        return True

    async def execute(self, state: AgentState, context: ExecutionContext) -> AgentResult:
        logger.info("Tool Executor initiating run.")
        start_time = time.perf_counter()
        
        # Build execution request context
        user_id = str(context.user_id)
        workspace_id = str(context.workspace_id)
        execution_id = context.request_id or "exec-default"
        db = context.configuration.get("db")
        
        # 1. Resolve target tool from step action
        action = "calculator" # Default action
        args = {"operation": "multiply", "a": 250, "b": 12} # Default args
        is_mcp_step = False
        mcp_tool_id: Optional[str] = None
        
        planner_output = state.get("agent_outputs", {}).get("PlannerAgent")
        if planner_output:
            try:
                plan_data = json.loads(planner_output["output"])
                for step in plan_data.get("steps", []):
                    if step.get("agent_type") == "TOOL_EXECUTOR":
                        action = step.get("action", "calculator")
                        if step.get("tool_source") == "MCP" or action.startswith("mcp:"):
                            is_mcp_step = True
                            mcp_tool_id = step.get("tool_id")
                        elif action in ("calculator", "calculator_tool"):
                            action = "calculator"
                        break
            except Exception:
                pass
                
        # Resolve prompt arguments if provided
        prompt = state.get("original_prompt", "")
        if "weather" in prompt.lower():
            action = "weather"
            args = {"location": "Seattle"}
            
        # Support token passing from state metadata
        conf_token = state.get("metadata", {}).get("confirmation_token")
        
        # Idempotency check
        idempotency_key = f"{execution_id}:{action}"
        if idempotency_key in self.executed_keys:
            logger.warning(f"Tool idempotency conflict detected for key: {idempotency_key}")
            raise ToolAlreadyExecuted()

        # Database Setup for ToolExecution
        tool_exec = None
        args_str = json.dumps(args, sort_keys=True)
        args_hash = hashlib.sha256(args_str.encode()).hexdigest()
        
        if db:
            from app.models.ai import ToolExecution
            from app.core.agent.graph import log_event
            try:
                tool_exec = ToolExecution(
                    execution_id=uuid.UUID(str(execution_id)) if isinstance(execution_id, str) and len(execution_id) == 36 else uuid.uuid4(),
                    tool_id=action,
                    arguments_hash=args_hash,
                    status="RUNNING",
                    started_at=datetime.datetime.now(datetime.timezone.utc),
                    retry_count=state.get("metadata", {}).get("tool_retries", 0)
                )
                db.add(tool_exec)
                db.commit()
                
                log_event(db, str(execution_id), "ToolStarted", agent_type=self.name, status="success", metadata={"tool_id": action})
            except Exception as e:
                logger.error(f"Failed to record tool execution start: {e}")

        try:
            # 2. Check if this is an MCP Tool, Resource, or Prompt invocation
            if (is_mcp_step or action.startswith("mcp:")) and db:
                from app.services.mcp.mcp_tool_executor import MCPToolExecutionService
                from app.services.mcp.mcp_tool_catalog import MCPToolCatalogService
                from app.services.mcp.mcp_resource_service import MCPResourceService
                from app.services.mcp.mcp_prompt_service import MCPPromptService
                from app.core.mcp.base import MCPToolConfirmationRequired

                clean_mcp_name = action[4:] if action.startswith("mcp:") else action

                # A. MCP Resource read flow
                if clean_mcp_name in ("read_resource", "resource_read") or (planner_output and "RESOURCE" in planner_output.get("output", "")):
                    resource_service = MCPResourceService(db)
                    target_res_id = mcp_tool_id
                    target_res_name = "MCP Resource"
                    if not target_res_id:
                        res_items, _ = resource_service.list_resources(uuid.UUID(user_id), uuid.UUID(workspace_id), limit=1)
                        if res_items:
                            target_res_id = str(res_items[0]["id"])
                            target_res_name = res_items[0].get("name", "MCP Resource")
                    
                    if not target_res_id:
                        raise ToolNotFound("No active MCP resources available in this workspace.")

                    res_read = await resource_service.read_resource(
                        user_id=uuid.UUID(user_id),
                        workspace_id=uuid.UUID(workspace_id),
                        resource_id=uuid.UUID(target_res_id)
                    )
                    resource_text = res_read.text or ""
                    state["mcp_resource_context"] = resource_text
                    elapsed = time.perf_counter() - start_time
                    tool_res = ToolExecutionResult(
                        execution_id=execution_id,
                        tool_id=action,
                        status=ToolExecutionStatus.SUCCESS,
                        output={"content": resource_text, "uri": res_read.uri, "mime_type": res_read.mime_type},
                        execution_time=elapsed,
                        metadata={"source": "MCP_RESOURCE", "resource_id": target_res_id, "uri": res_read.uri, "title": target_res_name, "trust_label": "UNTRUSTED_MCP"}
                    )

                # B. MCP Prompt render flow
                elif clean_mcp_name in ("render_prompt", "prompt_render") or (planner_output and "PROMPT" in planner_output.get("output", "")):
                    prompt_service = MCPPromptService(db)
                    target_pr_id = mcp_tool_id
                    if not target_pr_id:
                        pr_items, _ = prompt_service.list_prompts(uuid.UUID(user_id), uuid.UUID(workspace_id), limit=1)
                        if pr_items:
                            target_pr_id = str(pr_items[0]["id"])

                    if not target_pr_id:
                        raise ToolNotFound("No active MCP prompts available in this workspace.")

                    pr_rendered = await prompt_service.render_prompt(
                        user_id=uuid.UUID(user_id),
                        workspace_id=uuid.UUID(workspace_id),
                        prompt_id=uuid.UUID(target_pr_id),
                        arguments=args
                    )
                    msg_list = [m.model_dump() if hasattr(m, "model_dump") else m for m in pr_rendered.messages]
                    state["mcp_prompt_context"] = json.dumps(msg_list)
                    elapsed = time.perf_counter() - start_time
                    tool_res = ToolExecutionResult(
                        execution_id=execution_id,
                        tool_id=action,
                        status=ToolExecutionStatus.SUCCESS,
                        output={"messages": msg_list, "description": pr_rendered.description},
                        execution_time=elapsed,
                        metadata={"source": "MCP_PROMPT", "prompt_id": target_pr_id, "name": pr_rendered.name, "trust_label": "UNTRUSTED_MCP"}
                    )

                # C. MCP Tool execution flow
                else:
                    catalog = MCPToolCatalogService(db)
                    target_tool = None
                    if mcp_tool_id:
                        target_tool = catalog.get_tool(uuid.UUID(user_id), uuid.UUID(workspace_id), uuid.UUID(mcp_tool_id))
                    if not target_tool:
                        candidates = catalog.search_tools(uuid.UUID(user_id), uuid.UUID(workspace_id), query=clean_mcp_name if clean_mcp_name != "execute_tool" else "", limit=1)
                        if candidates:
                            target_tool = candidates[0]

                    if not target_tool:
                        raise ToolNotFound(f"MCP tool '{action}' not found in workspace catalog.")

                    mcp_executor = MCPToolExecutionService(db)
                    try:
                        mcp_res = await mcp_executor.execute_tool(
                            user_id=uuid.UUID(user_id),
                            workspace_id=uuid.UUID(workspace_id),
                            tool_id=uuid.UUID(str(target_tool["id"])),
                            arguments=args,
                            confirmation_token=conf_token,
                            timeout=15.0
                        )
                    except MCPToolConfirmationRequired as mcr:
                        state["mcp_pending_confirmation"] = {
                            "tool_id": str(target_tool["id"]),
                            "tool_name": target_tool["name"],
                            "risk_reasons": mcr.risk_reasons
                        }
                        raise ToolConfirmationRequired(mcr.risk_reasons)

                    elapsed = time.perf_counter() - start_time
                    tool_res = ToolExecutionResult(
                        execution_id=execution_id,
                        tool_id=action,
                        status=ToolExecutionStatus.SUCCESS,
                        output=mcp_res.result,
                        execution_time=elapsed,
                        metadata={
                            "source": "MCP",
                            "tool_id": str(target_tool["id"]),
                            "tool_name": target_tool["name"],
                            "server_id": str(target_tool.get("server_id", "")),
                            "trust_label": "UNTRUSTED_MCP"
                        }
                    )

            else:
                # 3. Retrieve and execute local tool from registry
                tool = self.registry.get(action)
                defn = tool.definition()
                
                # Enforce active check
                if not defn.enabled:
                    raise ToolDisabled()
                    
                # Permission guard check
                required_perms = defn.required_permissions
                if required_perms:
                    user_perms = context.permissions or []
                    if not any(p in user_perms for p in required_perms):
                        raise ToolPermissionDenied(f"ExecutionContext lacks permission: {required_perms}")
                        
                # Argument validations
                tool.validate_arguments(args)
                
                # Check confirmation system
                if defn.requires_confirmation:
                    expected_token = generate_confirmation_token(
                        execution_id, action, user_id, workspace_id, args
                    )
                    if not conf_token:
                        logger.info("Human confirmation token required for tool run.")
                        elapsed = time.perf_counter() - start_time
                        tool_res = ToolExecutionResult(
                            execution_id=execution_id,
                            tool_id=action,
                            status=ToolExecutionStatus.REQUIRES_CONFIRMATION,
                            error="Human confirmation required.",
                            execution_time=elapsed,
                            metadata={"confirmation_token": expected_token}
                        )
                        
                        if db and tool_exec:
                            try:
                                tool_exec.status = "REQUIRES_CONFIRMATION"
                                tool_exec.completed_at = datetime.datetime.now(datetime.timezone.utc)
                                tool_exec.result = "Requires human confirmation."
                                db.commit()
                            except Exception as db_err:
                                logger.error(f"Failed to update tool state to confirmation: {db_err}")

                        tool_results_list = state.get("tool_results", [])
                        tool_results_list.append(tool_res.model_dump())
                        
                        return AgentResult(
                            agent_name=self.name,
                            status="requires_confirmation",
                            output=tool_res.model_dump_json(),
                            confidence=1.0,
                            execution_time=elapsed,
                            token_usage={"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}
                        )
                    elif conf_token != expected_token:
                        raise ToolConfirmationInvalid()

                # Execute the local tool
                ctx = {"user_id": user_id, "workspace_id": workspace_id}
                output = await tool.execute(args, ctx)
                elapsed = time.perf_counter() - start_time
                
                tool_res = ToolExecutionResult(
                    execution_id=execution_id,
                    tool_id=action,
                    status=ToolExecutionStatus.SUCCESS,
                    output=output,
                    execution_time=elapsed
                )

            # Update DB ToolExecution record
            if db and tool_exec:
                try:
                    tool_exec.status = "COMPLETED"
                    tool_exec.completed_at = datetime.datetime.now(datetime.timezone.utc)
                    tool_exec.result = str(tool_res.output)
                    db.commit()
                    
                    from app.core.agent.graph import log_event
                    log_event(db, str(execution_id), "ToolCompleted", agent_type=self.name, status="success", metadata={"tool_id": action})
                except Exception as db_err:
                    logger.error(f"Failed to update tool completion: {db_err}")
            
            # Save idempotency record
            self.executed_keys[idempotency_key] = tool_res
            
            # Append tool result to agent state tool_results
            tool_results_list = state.get("tool_results", [])
            tool_results_list.append(tool_res.model_dump())

            return AgentResult(
                agent_name=self.name,
                status="success",
                output=tool_res.model_dump_json(),
                confidence=1.0,
                execution_time=elapsed,
                token_usage={"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
            )

        except Exception as e:
            logger.error(f"ToolExecutorAgent execution failure: {e}")
            if db and tool_exec:
                try:
                    tool_exec.status = "FAILED"
                    tool_exec.completed_at = datetime.datetime.now(datetime.timezone.utc)
                    tool_exec.error = str(e)
                    db.commit()
                except Exception:
                    pass
            raise e
