import uuid
import time
import json
import hashlib
import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from loguru import logger

from app.models.mcp import MCPServer, MCPCapability, MCPCapabilityType, MCPServerStatus
from app.models.ai import ToolExecution
from app.core.mcp.base import (
    BaseMCPClient,
    MCPToolExecutionResult,
    MCPClientError,
    MCPConnectionError,
    MCPValidationError,
    MCPTimeoutError,
    MCPAuthError,
    MCPToolConfirmationRequired
)
from app.core.mcp.connection import MCPConnectionManager
from app.core.mcp.policy import ToolRiskPolicy, ToolRiskLevel, ToolPolicyDecision
from app.core.mcp.security import CredentialStore
from app.core.mcp.normalization import MCPNormalizer

# In-memory single-use confirmation token registry and fallback execution locks
_CONFIRMATION_TOKENS: Dict[str, Dict[str, Any]] = {}
_LOCAL_EXECUTION_LOCKS = set()

def generate_tool_confirmation_token(
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
    tool_id: uuid.UUID,
    arguments: Dict[str, Any],
    expires_in_seconds: int = 300
) -> str:
    """
    Generates a cryptographically secure, single-use confirmation token bound
    to the specific user, workspace, tool ID, and arguments hash.
    """
    args_hash = hashlib.sha256(json.dumps(arguments, sort_keys=True).encode()).hexdigest()
    raw_token = f"{user_id}:{workspace_id}:{tool_id}:{args_hash}:{uuid.uuid4()}"
    token = hashlib.sha256(raw_token.encode()).hexdigest()

    expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expires_in_seconds)
    _CONFIRMATION_TOKENS[token] = {
        "user_id": str(user_id),
        "workspace_id": str(workspace_id),
        "tool_id": str(tool_id),
        "args_hash": args_hash,
        "expires_at": expiry
    }
    return token

def verify_and_consume_confirmation_token(
    token: str,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
    tool_id: uuid.UUID,
    arguments: Dict[str, Any]
) -> bool:
    """
    Validates token correctness, non-expiration, tenant binding, and single-use consumption.
    """
    if not token or token not in _CONFIRMATION_TOKENS:
        return False

    entry = _CONFIRMATION_TOKENS.pop(token) # Single-use consumption
    now = datetime.datetime.now(datetime.timezone.utc)

    if now > entry["expires_at"]:
        logger.warning("MCP tool confirmation token expired.")
        return False

    args_hash = hashlib.sha256(json.dumps(arguments, sort_keys=True).encode()).hexdigest()

    if (
        entry["user_id"] != str(user_id)
        or entry["workspace_id"] != str(workspace_id)
        or entry["tool_id"] != str(tool_id)
        or entry["args_hash"] != args_hash
    ):
        logger.warning("MCP tool confirmation token binding mismatch.")
        return False

    return True


class MCPToolExecutionService:
    """
    Service managing safe, tenant-isolated MCP tool executions with JSON Schema validation,
    deterministic risk policies, human confirmation gating, retry handling, and output sanitization.
    """
    DEFAULT_TIMEOUT = 15.0
    MAX_TIMEOUT = 60.0

    def __init__(self, db: Session, redis_client: Optional[Any] = None):
        self.db = db
        self.redis = redis_client

    def validate_tool_and_server(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        tool_id: uuid.UUID
    ) -> tuple[MCPCapability, MCPServer]:
        result = self.db.query(MCPCapability, MCPServer).join(
            MCPServer, MCPCapability.server_id == MCPServer.id
        ).filter(
            and_(
                MCPCapability.id == tool_id,
                MCPServer.user_id == user_id,
                MCPServer.workspace_id == workspace_id,
                MCPCapability.capability_type == MCPCapabilityType.TOOL,
                MCPCapability.deleted_at.is_(None),
                MCPServer.deleted_at.is_(None)
            )
        ).first()

        if not result:
            raise MCPValidationError(f"MCP tool not found or access denied for ID: {tool_id}")

        cap, server = result

        if not server.enabled:
            raise MCPValidationError(f"Cannot execute tool: MCP server '{server.name}' is disabled.")
        if server.status != MCPServerStatus.ACTIVE:
            raise MCPValidationError(f"Cannot execute tool: MCP server '{server.name}' status is {server.status.value}.")
        if not cap.enabled:
            raise MCPValidationError(f"Cannot execute tool: Tool '{cap.name}' is disabled.")
        if cap.is_stale:
            raise MCPValidationError(f"Cannot execute tool: Tool '{cap.name}' is stale / removed on server.")

        return cap, server

    def validate_arguments(self, arguments: Dict[str, Any], input_schema: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(arguments, dict):
            raise MCPValidationError("Tool arguments must be a JSON object dictionary.")

        # Total arguments payload bounded limit (32KB)
        args_json = json.dumps(arguments)
        if len(args_json.encode("utf-8")) > 32 * 1024:
            raise MCPValidationError("Tool arguments payload exceeds maximum size limit of 32KB.")

        if not input_schema:
            return arguments

        required_props = input_schema.get("required", [])
        for req in required_props:
            if req not in arguments or arguments[req] is None:
                raise MCPValidationError(f"Missing required parameter '{req}' for tool execution.")

        properties = input_schema.get("properties", {})
        for key, val in arguments.items():
            if key in properties:
                expected_type = properties[key].get("type")
                if expected_type == "string" and not isinstance(val, str):
                    raise MCPValidationError(f"Parameter '{key}' must be a string (got {type(val).__name__}).")
                elif expected_type == "number" and not isinstance(val, (int, float)):
                    raise MCPValidationError(f"Parameter '{key}' must be a number (got {type(val).__name__}).")
                elif expected_type == "integer" and not isinstance(val, int):
                    raise MCPValidationError(f"Parameter '{key}' must be an integer (got {type(val).__name__}).")
                elif expected_type == "boolean" and not isinstance(val, bool):
                    raise MCPValidationError(f"Parameter '{key}' must be a boolean (got {type(val).__name__}).")
                elif expected_type == "array" and not isinstance(val, list):
                    raise MCPValidationError(f"Parameter '{key}' must be an array (got {type(val).__name__}).")
                elif expected_type == "object" and not isinstance(val, dict):
                    raise MCPValidationError(f"Parameter '{key}' must be an object (got {type(val).__name__}).")

        return arguments

    def sanitize_output(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitizes raw MCP server execution outputs, redacting sensitive tokens
        and preventing malicious payload injection into agent downstream context.
        """
        redacted = CredentialStore.redact_sensitive_dict(output)
        return redacted

    async def execute_tool(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        tool_id: uuid.UUID,
        arguments: Dict[str, Any],
        confirmation_token: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT
    ) -> MCPToolExecutionResult:
        start_time = time.perf_counter()
        execution_id = str(uuid.uuid4())

        # 1. Validate Tool and Server Tenant Existence
        cap, server = self.validate_tool_and_server(user_id, workspace_id, tool_id)

        # 2. Validate Arguments Schema
        valid_args = self.validate_arguments(arguments, cap.input_schema)

        # 3. Assess Safety & Risk Policy
        risk = ToolRiskPolicy.assess_tool(
            name=cap.name,
            description=cap.description,
            input_schema=cap.input_schema,
            meta_data=cap.meta_data
        )

        if risk["risk_level"] == ToolRiskLevel.INVALID.value:
            raise MCPValidationError(f"Tool execution denied: Tool is classified as INVALID. Reasons: {', '.join(risk['risk_reasons'])}")

        if risk["risk_level"] == ToolRiskLevel.RESTRICTED.value:
            if not confirmation_token:
                raise MCPToolConfirmationRequired(
                    message=f"Human confirmation required to execute RESTRICTED tool '{cap.name}'.",
                    tool_id=str(cap.id),
                    risk_reasons=risk["risk_reasons"]
                )

            valid_conf = verify_and_consume_confirmation_token(
                token=confirmation_token,
                user_id=user_id,
                workspace_id=workspace_id,
                tool_id=tool_id,
                arguments=valid_args
            )
            if not valid_conf:
                raise MCPValidationError("Invalid or expired tool execution confirmation token.")

        # 4. Acquire Concurrency Lock
        lock_key = f"aegis:mcp:exec:{tool_id}:{user_id}"
        if lock_key in _LOCAL_EXECUTION_LOCKS:
            raise MCPValidationError("Tool execution already in progress. Please wait.")
        _LOCAL_EXECUTION_LOCKS.add(lock_key)

        client: Optional[BaseMCPClient] = None
        effective_timeout = min(max(timeout, 1.0), self.MAX_TIMEOUT)

        try:
            # 5. Connect and Handshake
            client, _ = await MCPConnectionManager.connect_and_initialize(
                server_url=server.server_url,
                transport=server.transport,
                auth_config=server.auth_config,
                timeout=effective_timeout
            )

            # 6. Execute Named Tool with Exponential Retries for Transient Errors
            async def _call_op():
                return await client.call_tool(cap.name, valid_args)

            raw_result = await MCPConnectionManager.execute_with_retry(_call_op, max_retries=2)
            sanitized_result = self.sanitize_output(raw_result)

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # 7. Persist Execution Record in DB safely
            try:
                args_hash = hashlib.sha256(json.dumps(valid_args, sort_keys=True).encode()).hexdigest()
                tool_exec = ToolExecution(
                    id=uuid.uuid4(),
                    execution_id=uuid.UUID(execution_id),
                    tool_id=f"mcp:{cap.name}",
                    status="SUCCESS",
                    arguments_hash=args_hash,
                    started_at=datetime.datetime.now(datetime.timezone.utc),
                    completed_at=datetime.datetime.now(datetime.timezone.utc),
                    result=json.dumps(sanitized_result)
                )
                self.db.add(tool_exec)
                self.db.commit()
            except Exception as db_err:
                logger.debug(f"Optional DB execution persistence skipped: {db_err}")
                self.db.rollback()

            return MCPToolExecutionResult(
                execution_id=execution_id,
                tool_id=str(cap.id),
                tool_name=cap.name,
                status="SUCCESS",
                result=sanitized_result,
                text_content=sanitized_result.get("text") or str(sanitized_result),
                duration_ms=round(elapsed_ms, 2)
            )

        except MCPToolConfirmationRequired as cr:
            raise cr
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            err_msg = str(e)
            logger.error(f"MCP tool execution failed for '{cap.name}': {err_msg}")

            # Persist failure record
            try:
                args_hash = hashlib.sha256(json.dumps(valid_args, sort_keys=True).encode()).hexdigest()
                tool_exec = ToolExecution(
                    id=uuid.uuid4(),
                    execution_id=uuid.UUID(execution_id),
                    tool_id=f"mcp:{cap.name}",
                    status="FAILED",
                    arguments_hash=args_hash,
                    started_at=datetime.datetime.now(datetime.timezone.utc),
                    completed_at=datetime.datetime.now(datetime.timezone.utc),
                    error=err_msg
                )
                self.db.add(tool_exec)
                self.db.commit()
            except Exception:
                self.db.rollback()

            if isinstance(e, MCPClientError):
                raise e
            raise MCPValidationError(f"Execution failed: {err_msg}")

        finally:
            _LOCAL_EXECUTION_LOCKS.discard(lock_key)
            if client:
                await client.close()
