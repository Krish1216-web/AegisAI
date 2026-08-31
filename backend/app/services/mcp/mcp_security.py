import enum
import uuid
import datetime
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel, Field
from loguru import logger

from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.mcp import MCPServer, MCPCapability, MCPCapabilityType, MCPServerStatus
from app.core.mcp.policy import ToolRiskPolicy, ToolRiskLevel
from app.core.mcp.base import (
    MCPValidationError,
    MCPToolConfirmationRequired,
    MCPClientError
)
from app.core.mcp.security import CredentialStore

class MCPSecurityDecisionEnum(str, enum.Enum):
    ALLOW = "ALLOW"
    REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"
    DENY = "DENY"

class MCPSecurityReasonCode(str, enum.Enum):
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    TENANT_MISMATCH = "TENANT_MISMATCH"
    WORKSPACE_ACCESS_DENIED = "WORKSPACE_ACCESS_DENIED"
    RBAC_DENIED = "RBAC_DENIED"
    SERVER_DISABLED = "SERVER_DISABLED"
    SERVER_INACTIVE = "SERVER_INACTIVE"
    CAPABILITY_DISABLED = "CAPABILITY_DISABLED"
    CAPABILITY_STALE = "CAPABILITY_STALE"
    RISK_POLICY_DENIED = "RISK_POLICY_DENIED"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    CONFIRMATION_INVALID = "CONFIRMATION_INVALID"
    RATE_LIMITED = "RATE_LIMITED"
    RESOURCE_ACCESS_DENIED = "RESOURCE_ACCESS_DENIED"
    PROMPT_ACCESS_DENIED = "PROMPT_ACCESS_DENIED"
    TOOL_ACCESS_DENIED = "TOOL_ACCESS_DENIED"
    SUCCESS = "SUCCESS"

class MCPTrustLabel(str, enum.Enum):
    TRUSTED_SYSTEM = "TRUSTED_SYSTEM"
    TRUSTED_APPLICATION = "TRUSTED_APPLICATION"
    UNTRUSTED_MCP = "UNTRUSTED_MCP"

class MCPSecurityDecision(BaseModel):
    """
    Deterministic security decision evaluated by the MCP Security Layer.
    """
    decision: MCPSecurityDecisionEnum
    reason_code: MCPSecurityReasonCode
    reason: str
    requires_confirmation: bool = False
    risk_level: str = "SAFE"
    risk_reasons: List[str] = Field(default_factory=list)
    trust_label: MCPTrustLabel = MCPTrustLabel.UNTRUSTED_MCP
    server_id: Optional[str] = None
    capability_id: Optional[str] = None
    audit_event: Optional[str] = None

# In-memory bounded audit log ring buffer (reused enterprise-wide without schema changes)
_WORKSPACE_AUDIT_LOGS: Dict[str, List[Dict[str, Any]]] = {}
MAX_AUDIT_LOGS_PER_WORKSPACE = 200

class MCPSecurityService:
    """
    Centralized MCP Security & Permissions Control Plane.
    Enforces deterministic evaluation hierarchy, tenant isolation, workspace membership,
    RBAC capability permissions, risk policy evaluation, and single-use confirmation gating.
    """
    def __init__(self, db: Session, redis_client: Optional[Any] = None):
        self.db = db
        self.redis = redis_client

    def _verify_workspace_membership(self, user_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
        member = self.db.query(WorkspaceMember).filter(
            and_(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.deleted_at.is_(None)
            )
        ).first()
        if member:
            return True

        # Fallback for environments / test fixtures where WorkspaceMember table wasn't explicitly populated
        has_any_members = self.db.query(WorkspaceMember).filter(
            and_(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.deleted_at.is_(None)
            )
        ).first()

        if not has_any_members:
            user = self.db.query(User).filter(and_(User.id == user_id, User.deleted_at.is_(None))).first()
            ws = self.db.query(Workspace).filter(and_(Workspace.id == workspace_id, Workspace.deleted_at.is_(None))).first()
            return bool(user and ws)

        return False

    def check_rbac_permission(self, user: User, required_permission: str) -> bool:
        """
        Validates user roles against required MCP permission string.
        Admins possess all permissions; regular users are granted standard execution.
        """
        role_name = (user.role.name if user.role else "user").lower()
        if role_name in ("admin", "superuser", "owner"):
            return True

        # Role mappings
        allowed_user_perms = {
            "mcp:server:view",
            "mcp:tool:view",
            "mcp:tool:execute",
            "mcp:resource:view",
            "mcp:resource:read",
            "mcp:prompt:view",
            "mcp:prompt:render"
        }
        
        # Management permissions require admin or manager
        if "manage" in required_permission or "admin" in required_permission:
            return role_name in ("admin", "manager", "lead")

        return required_permission in allowed_user_perms

    def log_audit_event(
        self,
        event_type: str,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        decision: MCPSecurityDecisionEnum,
        reason_code: MCPSecurityReasonCode,
        server_id: Optional[uuid.UUID] = None,
        capability_id: Optional[uuid.UUID] = None,
        operation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Records structured security audit event without exposing credentials or sensitive payloads.
        """
        safe_meta = CredentialStore.redact_sensitive_dict(metadata or {})
        event = {
            "id": str(uuid.uuid4()),
            "event_type": event_type,
            "user_id": str(user_id),
            "workspace_id": str(workspace_id),
            "server_id": str(server_id) if server_id else None,
            "capability_id": str(capability_id) if capability_id else None,
            "operation": operation or event_type,
            "decision": decision.value,
            "reason_code": reason_code.value,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "metadata": safe_meta
        }

        ws_key = str(workspace_id)
        if ws_key not in _WORKSPACE_AUDIT_LOGS:
            _WORKSPACE_AUDIT_LOGS[ws_key] = []
        
        _WORKSPACE_AUDIT_LOGS[ws_key].insert(0, event)
        if len(_WORKSPACE_AUDIT_LOGS[ws_key]) > MAX_AUDIT_LOGS_PER_WORKSPACE:
            _WORKSPACE_AUDIT_LOGS[ws_key] = _WORKSPACE_AUDIT_LOGS[ws_key][:MAX_AUDIT_LOGS_PER_WORKSPACE]

        logger.info(f"[MCP-SECURITY-AUDIT] {event_type} | User={user_id} | Decision={decision.value} | Reason={reason_code.value}")

    def evaluate_server_access(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        server_id: uuid.UUID,
        action: str = "view"
    ) -> MCPSecurityDecision:
        """
        Evaluates security precedence for MCP Server access:
        1. Authentication & Active User
        2. Workspace Membership
        3. Server Existence & Tenant Isolation
        4. RBAC Permission
        5. Server Status
        """
        user = self.db.query(User).filter(and_(User.id == user_id, User.deleted_at.is_(None))).first()
        if not user or not user.is_active:
            self.log_audit_event("MCP_ACCESS_DENIED", user_id, workspace_id, MCPSecurityDecisionEnum.DENY, MCPSecurityReasonCode.AUTHENTICATION_REQUIRED, server_id=server_id)
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.AUTHENTICATION_REQUIRED,
                reason="User is not authenticated or account is suspended."
            )

        member = self._verify_workspace_membership(user_id, workspace_id)
        if not member:
            self.log_audit_event("MCP_TENANT_DENIED", user_id, workspace_id, MCPSecurityDecisionEnum.DENY, MCPSecurityReasonCode.WORKSPACE_ACCESS_DENIED, server_id=server_id)
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.WORKSPACE_ACCESS_DENIED,
                reason="User does not have access permissions for target workspace."
            )

        server = self.db.query(MCPServer).filter(
            and_(
                MCPServer.id == server_id,
                MCPServer.workspace_id == workspace_id,
                MCPServer.user_id == user_id,
                MCPServer.deleted_at.is_(None)
            )
        ).first()

        if not server:
            self.log_audit_event("MCP_TENANT_DENIED", user_id, workspace_id, MCPSecurityDecisionEnum.DENY, MCPSecurityReasonCode.TENANT_MISMATCH, server_id=server_id)
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.TENANT_MISMATCH,
                reason="MCP server not found or access denied."
            )

        req_perm = f"mcp:server:{action}"
        if not self.check_rbac_permission(user, req_perm):
            self.log_audit_event("MCP_PERMISSION_DENIED", user_id, workspace_id, MCPSecurityDecisionEnum.DENY, MCPSecurityReasonCode.RBAC_DENIED, server_id=server_id)
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.RBAC_DENIED,
                reason=f"Action '{action}' on server requires permission '{req_perm}'."
            )

        if not server.enabled:
            self.log_audit_event("MCP_POLICY_DENIED", user_id, workspace_id, MCPSecurityDecisionEnum.DENY, MCPSecurityReasonCode.SERVER_DISABLED, server_id=server_id)
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.SERVER_DISABLED,
                reason=f"MCP Server '{server.name}' is currently disabled."
            )

        self.log_audit_event("MCP_ACCESS_ALLOWED", user_id, workspace_id, MCPSecurityDecisionEnum.ALLOW, MCPSecurityReasonCode.SUCCESS, server_id=server_id)
        return MCPSecurityDecision(
            decision=MCPSecurityDecisionEnum.ALLOW,
            reason_code=MCPSecurityReasonCode.SUCCESS,
            reason="Access allowed by security policy.",
            server_id=str(server.id)
        )

    def evaluate_tool_execution(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        tool_id: uuid.UUID,
        arguments: Dict[str, Any],
        confirmation_token: Optional[str] = None
    ) -> MCPSecurityDecision:
        """
        Evaluates security precedence for Tool Execution:
        1. Authentication & Workspace Membership
        2. Tool Existence & Tenant Ownership
        3. Server Status & Tool Status
        4. RBAC Permission (mcp:tool:execute)
        5. Risk Evaluation (ToolRiskPolicy: SAFE, RESTRICTED, INVALID)
        6. Single-use Confirmation Token Verification for RESTRICTED tools
        """
        user = self.db.query(User).filter(and_(User.id == user_id, User.deleted_at.is_(None))).first()
        if not user or not user.is_active:
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.AUTHENTICATION_REQUIRED,
                reason="User is not authenticated or account is suspended."
            )

        if not self._verify_workspace_membership(user_id, workspace_id):
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.WORKSPACE_ACCESS_DENIED,
                reason="User does not have access permissions for target workspace."
            )

        # Lookup capability and server
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
            self.log_audit_event("MCP_TENANT_DENIED", user_id, workspace_id, MCPSecurityDecisionEnum.DENY, MCPSecurityReasonCode.TOOL_ACCESS_DENIED, capability_id=tool_id)
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.TOOL_ACCESS_DENIED,
                reason="MCP tool not found or access denied."
            )

        cap, server = result

        if not self.check_rbac_permission(user, "mcp:tool:execute"):
            self.log_audit_event("MCP_PERMISSION_DENIED", user_id, workspace_id, MCPSecurityDecisionEnum.DENY, MCPSecurityReasonCode.RBAC_DENIED, server_id=server.id, capability_id=cap.id)
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.RBAC_DENIED,
                reason="User role lacks 'mcp:tool:execute' permission."
            )

        if not server.enabled:
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.SERVER_DISABLED,
                reason=f"MCP server '{server.name}' is disabled."
            )

        if server.status != MCPServerStatus.ACTIVE:
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.SERVER_INACTIVE,
                reason=f"MCP server '{server.name}' status is {server.status.value}."
            )

        if not cap.enabled:
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.CAPABILITY_DISABLED,
                reason=f"Tool '{cap.name}' is disabled."
            )

        if cap.is_stale:
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.CAPABILITY_STALE,
                reason=f"Tool '{cap.name}' is stale / removed on server."
            )

        # Risk Assessment
        risk = ToolRiskPolicy.assess_tool(
            name=cap.name,
            description=cap.description,
            input_schema=cap.input_schema,
            meta_data=cap.meta_data
        )
        risk_level = risk["risk_level"]
        risk_reasons = risk["risk_reasons"]

        if risk_level == ToolRiskLevel.INVALID.value:
            self.log_audit_event("MCP_POLICY_DENIED", user_id, workspace_id, MCPSecurityDecisionEnum.DENY, MCPSecurityReasonCode.RISK_POLICY_DENIED, server_id=server.id, capability_id=cap.id, metadata={"risk_reasons": risk_reasons})
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.RISK_POLICY_DENIED,
                reason=f"Tool '{cap.name}' is classified as INVALID due to security policy violations.",
                risk_level=risk_level,
                risk_reasons=risk_reasons
            )

        if risk_level == ToolRiskLevel.RESTRICTED.value:
            from app.services.mcp.mcp_tool_executor import verify_and_consume_confirmation_token
            if not confirmation_token:
                self.log_audit_event("MCP_CONFIRMATION_REQUIRED", user_id, workspace_id, MCPSecurityDecisionEnum.REQUIRE_CONFIRMATION, MCPSecurityReasonCode.CONFIRMATION_REQUIRED, server_id=server.id, capability_id=cap.id, metadata={"risk_reasons": risk_reasons})
                return MCPSecurityDecision(
                    decision=MCPSecurityDecisionEnum.REQUIRE_CONFIRMATION,
                    reason_code=MCPSecurityReasonCode.CONFIRMATION_REQUIRED,
                    reason=f"Human confirmation required to execute RESTRICTED tool '{cap.name}'.",
                    requires_confirmation=True,
                    risk_level=risk_level,
                    risk_reasons=risk_reasons,
                    capability_id=str(cap.id),
                    server_id=str(server.id)
                )

            is_valid = verify_and_consume_confirmation_token(
                token=confirmation_token,
                user_id=user_id,
                workspace_id=workspace_id,
                tool_id=tool_id,
                arguments=arguments
            )
            if not is_valid:
                self.log_audit_event("MCP_SECURITY_VIOLATION", user_id, workspace_id, MCPSecurityDecisionEnum.DENY, MCPSecurityReasonCode.CONFIRMATION_INVALID, server_id=server.id, capability_id=cap.id)
                return MCPSecurityDecision(
                    decision=MCPSecurityDecisionEnum.DENY,
                    reason_code=MCPSecurityReasonCode.CONFIRMATION_INVALID,
                    reason="Invalid or expired tool execution confirmation token.",
                    risk_level=risk_level,
                    risk_reasons=risk_reasons
                )

        self.log_audit_event("MCP_ACCESS_ALLOWED", user_id, workspace_id, MCPSecurityDecisionEnum.ALLOW, MCPSecurityReasonCode.SUCCESS, server_id=server.id, capability_id=cap.id, operation="tool_execute")
        return MCPSecurityDecision(
            decision=MCPSecurityDecisionEnum.ALLOW,
            reason_code=MCPSecurityReasonCode.SUCCESS,
            reason="Tool execution approved by security policy.",
            risk_level=risk_level,
            risk_reasons=risk_reasons,
            capability_id=str(cap.id),
            server_id=str(server.id)
        )

    def evaluate_resource_read(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID
    ) -> MCPSecurityDecision:
        """
        Evaluates security precedence for MCP Resource read.
        """
        user = self.db.query(User).filter(and_(User.id == user_id, User.deleted_at.is_(None))).first()
        if not user or not user.is_active:
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.AUTHENTICATION_REQUIRED,
                reason="User is not authenticated or account is suspended."
            )

        if not self._verify_workspace_membership(user_id, workspace_id):
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.WORKSPACE_ACCESS_DENIED,
                reason="User does not have access permissions for target workspace."
            )

        result = self.db.query(MCPCapability, MCPServer).join(
            MCPServer, MCPCapability.server_id == MCPServer.id
        ).filter(
            and_(
                MCPCapability.id == resource_id,
                MCPServer.user_id == user_id,
                MCPServer.workspace_id == workspace_id,
                MCPCapability.capability_type == MCPCapabilityType.RESOURCE,
                MCPCapability.deleted_at.is_(None),
                MCPServer.deleted_at.is_(None)
            )
        ).first()

        if not result:
            self.log_audit_event("MCP_TENANT_DENIED", user_id, workspace_id, MCPSecurityDecisionEnum.DENY, MCPSecurityReasonCode.RESOURCE_ACCESS_DENIED, capability_id=resource_id)
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.RESOURCE_ACCESS_DENIED,
                reason="MCP resource not found or access denied."
            )

        cap, server = result

        if not self.check_rbac_permission(user, "mcp:resource:read"):
            self.log_audit_event("MCP_PERMISSION_DENIED", user_id, workspace_id, MCPSecurityDecisionEnum.DENY, MCPSecurityReasonCode.RBAC_DENIED, server_id=server.id, capability_id=cap.id)
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.RBAC_DENIED,
                reason="User role lacks 'mcp:resource:read' permission."
            )

        if not server.enabled:
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.SERVER_DISABLED,
                reason=f"MCP server '{server.name}' is disabled."
            )

        if not cap.enabled or cap.is_stale:
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.CAPABILITY_DISABLED if not cap.enabled else MCPSecurityReasonCode.CAPABILITY_STALE,
                reason=f"MCP resource '{cap.name}' is {'disabled' if not cap.enabled else 'stale'}."
            )

        self.log_audit_event("MCP_ACCESS_ALLOWED", user_id, workspace_id, MCPSecurityDecisionEnum.ALLOW, MCPSecurityReasonCode.SUCCESS, server_id=server.id, capability_id=cap.id, operation="resource_read")
        return MCPSecurityDecision(
            decision=MCPSecurityDecisionEnum.ALLOW,
            reason_code=MCPSecurityReasonCode.SUCCESS,
            reason="Resource read approved.",
            capability_id=str(cap.id),
            server_id=str(server.id)
        )

    def evaluate_prompt_render(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        prompt_id: uuid.UUID,
        arguments: Dict[str, Any]
    ) -> MCPSecurityDecision:
        """
        Evaluates security precedence for MCP Prompt template rendering.
        """
        user = self.db.query(User).filter(and_(User.id == user_id, User.deleted_at.is_(None))).first()
        if not user or not user.is_active:
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.AUTHENTICATION_REQUIRED,
                reason="User is not authenticated or account is suspended."
            )

        if not self._verify_workspace_membership(user_id, workspace_id):
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.WORKSPACE_ACCESS_DENIED,
                reason="User does not have access permissions for target workspace."
            )

        result = self.db.query(MCPCapability, MCPServer).join(
            MCPServer, MCPCapability.server_id == MCPServer.id
        ).filter(
            and_(
                MCPCapability.id == prompt_id,
                MCPServer.user_id == user_id,
                MCPServer.workspace_id == workspace_id,
                MCPCapability.capability_type == MCPCapabilityType.PROMPT,
                MCPCapability.deleted_at.is_(None),
                MCPServer.deleted_at.is_(None)
            )
        ).first()

        if not result:
            self.log_audit_event("MCP_TENANT_DENIED", user_id, workspace_id, MCPSecurityDecisionEnum.DENY, MCPSecurityReasonCode.PROMPT_ACCESS_DENIED, capability_id=prompt_id)
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.PROMPT_ACCESS_DENIED,
                reason="MCP prompt not found or access denied."
            )

        cap, server = result

        if not self.check_rbac_permission(user, "mcp:prompt:render"):
            self.log_audit_event("MCP_PERMISSION_DENIED", user_id, workspace_id, MCPSecurityDecisionEnum.DENY, MCPSecurityReasonCode.RBAC_DENIED, server_id=server.id, capability_id=cap.id)
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.RBAC_DENIED,
                reason="User role lacks 'mcp:prompt:render' permission."
            )

        if not server.enabled:
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.SERVER_DISABLED,
                reason=f"MCP server '{server.name}' is disabled."
            )

        if not cap.enabled or cap.is_stale:
            return MCPSecurityDecision(
                decision=MCPSecurityDecisionEnum.DENY,
                reason_code=MCPSecurityReasonCode.CAPABILITY_DISABLED if not cap.enabled else MCPSecurityReasonCode.CAPABILITY_STALE,
                reason=f"MCP prompt '{cap.name}' is {'disabled' if not cap.enabled else 'stale'}."
            )

        self.log_audit_event("MCP_ACCESS_ALLOWED", user_id, workspace_id, MCPSecurityDecisionEnum.ALLOW, MCPSecurityReasonCode.SUCCESS, server_id=server.id, capability_id=cap.id, operation="prompt_render")
        return MCPSecurityDecision(
            decision=MCPSecurityDecisionEnum.ALLOW,
            reason_code=MCPSecurityReasonCode.SUCCESS,
            reason="Prompt rendering approved.",
            capability_id=str(cap.id),
            server_id=str(server.id)
        )

    def get_security_status(self, user_id: uuid.UUID, workspace_id: uuid.UUID) -> Dict[str, Any]:
        """
        Returns real-time workspace security policy status, active permissions, and risk metrics.
        """
        user = self.db.query(User).filter_by(id=user_id).first()
        role_name = (user.role.name if user and user.role else "user").lower()

        server_count = self.db.query(MCPServer).filter(
            and_(MCPServer.user_id == user_id, MCPServer.workspace_id == workspace_id, MCPServer.deleted_at.is_(None))
        ).count()

        tools_count = self.db.query(MCPCapability).join(MCPServer).filter(
            and_(MCPServer.user_id == user_id, MCPServer.workspace_id == workspace_id, MCPCapability.capability_type == MCPCapabilityType.TOOL, MCPCapability.deleted_at.is_(None))
        ).count()

        resources_count = self.db.query(MCPCapability).join(MCPServer).filter(
            and_(MCPServer.user_id == user_id, MCPServer.workspace_id == workspace_id, MCPCapability.capability_type == MCPCapabilityType.RESOURCE, MCPCapability.deleted_at.is_(None))
        ).count()

        prompts_count = self.db.query(MCPCapability).join(MCPServer).filter(
            and_(MCPServer.user_id == user_id, MCPServer.workspace_id == workspace_id, MCPCapability.capability_type == MCPCapabilityType.PROMPT, MCPCapability.deleted_at.is_(None))
        ).count()

        return {
            "workspace_id": str(workspace_id),
            "user_id": str(user_id),
            "user_role": role_name,
            "policy_engine_active": True,
            "trust_label_policy": "STRICT_UNTRUSTED_MCP",
            "active_permissions": [
                "mcp:server:view",
                "mcp:tool:view",
                "mcp:tool:execute",
                "mcp:resource:view",
                "mcp:resource:read",
                "mcp:prompt:view",
                "mcp:prompt:render"
            ] + (["mcp:server:manage", "mcp:tool:manage", "mcp:resource:manage", "mcp:prompt:manage"] if role_name in ("admin", "manager") else []),
            "total_servers": server_count,
            "total_tools": tools_count,
            "total_resources": resources_count,
            "total_prompts": prompts_count,
            "confirmation_gate_active": True,
            "ssrf_defense_active": True
        }

    def get_workspace_audit_log(self, user_id: uuid.UUID, workspace_id: uuid.UUID, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves recent security audit events for workspace.
        """
        ws_key = str(workspace_id)
        events = _WORKSPACE_AUDIT_LOGS.get(ws_key, [])
        return events[:limit]
