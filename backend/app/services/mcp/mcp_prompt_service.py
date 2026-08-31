import uuid
import json
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from loguru import logger

from app.models.mcp import MCPServer, MCPCapability, MCPCapabilityType, MCPServerStatus
from app.core.mcp.base import (
    BaseMCPClient,
    MCPPromptMessage,
    MCPPromptRenderResult,
    MCPClientError,
    MCPConnectionError,
    MCPValidationError,
    MCPTimeoutError
)
from app.core.mcp.connection import MCPConnectionManager
from app.core.mcp.validation import MCPValidator

class MCPPromptService:
    """
    Service managing tenant-isolated MCP prompt templates, discovery, argument validation,
    and safe rendering with strict untrusted data isolation.
    """
    def __init__(self, db: Session, redis_client: Optional[Any] = None):
        self.db = db
        self.redis = redis_client

    def _get_prompt_and_server(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        prompt_id: uuid.UUID
    ) -> Tuple[MCPCapability, MCPServer]:
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
            raise MCPValidationError(f"MCP prompt not found or access denied for ID: {prompt_id}")

        return result

    def _format_prompt(self, cap: MCPCapability, server: MCPServer) -> Dict[str, Any]:
        meta = cap.meta_data or {}
        input_sch = cap.input_schema or {}
        # In prompt capabilities, arguments are stored in input_schema or meta_data
        arguments = input_sch.get("arguments") or meta.get("arguments") or []

        return {
            "id": cap.id,
            "server_id": server.id,
            "server_name": server.name,
            "server_transport": server.transport.value if hasattr(server.transport, "value") else str(server.transport),
            "server_status": server.status.value if hasattr(server.status, "value") else str(server.status),
            "server_enabled": server.enabled,
            "name": cap.name,
            "description": cap.description,
            "arguments": arguments,
            "metadata": meta,
            "enabled": cap.enabled,
            "is_stale": cap.is_stale,
            "stale_at": cap.stale_at,
            "definition_hash": cap.definition_hash,
            "version": cap.version,
            "first_discovered_at": cap.first_discovered_at,
            "last_discovered_at": cap.last_discovered_at,
            "created_at": cap.created_at,
            "updated_at": cap.updated_at
        }

    def list_prompts(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        server_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        enabled_only: bool = False,
        include_stale: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        query = self.db.query(MCPCapability, MCPServer).join(
            MCPServer, MCPCapability.server_id == MCPServer.id
        ).filter(
            and_(
                MCPServer.user_id == user_id,
                MCPServer.workspace_id == workspace_id,
                MCPCapability.capability_type == MCPCapabilityType.PROMPT,
                MCPCapability.deleted_at.is_(None),
                MCPServer.deleted_at.is_(None)
            )
        )

        if server_id:
            query = query.filter(MCPServer.id == server_id)
        if enabled_only:
            query = query.filter(and_(MCPCapability.enabled.is_(True), MCPServer.enabled.is_(True)))
        if not include_stale:
            query = query.filter(MCPCapability.is_stale.is_(False))
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.filter(
                or_(
                    MCPCapability.name.ilike(term),
                    MCPCapability.description.ilike(term)
                )
            )

        total = query.count()
        rows = query.order_by(MCPCapability.name.asc()).offset(offset).limit(limit).all()
        return [self._format_prompt(cap, srv) for cap, srv in rows], total

    def get_prompt(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        prompt_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        try:
            cap, server = self._get_prompt_and_server(user_id, workspace_id, prompt_id)
            return self._format_prompt(cap, server)
        except MCPValidationError:
            return None

    def search_prompts(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        query: str,
        server_id: Optional[uuid.UUID] = None,
        enabled_only: bool = False,
        include_stale: bool = True,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        prompts, _ = self.list_prompts(
            user_id=user_id,
            workspace_id=workspace_id,
            server_id=server_id,
            enabled_only=enabled_only,
            include_stale=include_stale,
            limit=100
        )

        if not query or not query.strip():
            return prompts[:limit]

        q_lower = query.strip().lower()
        scored: List[Tuple[float, Dict[str, Any]]] = []

        for p in prompts:
            score = 0.0
            p_name = p["name"].lower()
            p_desc = (p.get("description") or "").lower()

            if p_name == q_lower:
                score += 100.0
            elif p_name.startswith(q_lower):
                score += 80.0
            elif q_lower in p_name:
                score += 60.0
            elif q_lower in p_desc:
                score += 40.0

            if score > 0:
                scored.append((score, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    def toggle_prompt(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        prompt_id: uuid.UUID,
        enabled: bool
    ) -> Optional[Dict[str, Any]]:
        try:
            cap, server = self._get_prompt_and_server(user_id, workspace_id, prompt_id)
            cap.enabled = enabled
            self.db.commit()
            self.db.refresh(cap)
            return self._format_prompt(cap, server)
        except MCPValidationError:
            return None

    async def render_prompt(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        prompt_id: uuid.UUID,
        arguments: Dict[str, Any],
        timeout: float = 15.0
    ) -> MCPPromptRenderResult:
        # Central Security Layer Check
        from app.services.mcp.mcp_security import MCPSecurityService, MCPSecurityDecisionEnum
        sec_service = MCPSecurityService(self.db, self.redis)
        decision = sec_service.evaluate_prompt_render(user_id, workspace_id, prompt_id, arguments)
        if decision.decision != MCPSecurityDecisionEnum.ALLOW:
            raise MCPValidationError(f"Cannot render prompt: {decision.reason}")

        cap, server = self._get_prompt_and_server(user_id, workspace_id, prompt_id)

        # Validate arguments against prompt definition
        formatted = self._format_prompt(cap, server)
        prompt_def_args = formatted.get("arguments", [])
        valid_args = MCPValidator.validate_prompt_arguments(arguments, prompt_def_args)

        client: Optional[BaseMCPClient] = None
        try:
            client, _ = await MCPConnectionManager.connect_and_initialize(
                server_url=server.server_url,
                transport=server.transport,
                auth_config=server.auth_config,
                timeout=timeout
            )

            raw_res = await client.get_prompt(cap.name, valid_args)
            raw_messages = raw_res.get("messages", [])

            rendered_msgs: List[MCPPromptMessage] = []
            for msg in raw_messages:
                # CRITICAL SECURITY RULE: Role is normalized to 'user' or 'assistant', never elevated to system
                r = msg.get("role", "user")
                c = msg.get("content", "")
                rendered_msgs.append(MCPPromptMessage(
                    role=r,
                    content=c,
                    untrusted=True
                ))

            return MCPPromptRenderResult(
                prompt_id=str(cap.id),
                name=cap.name,
                description=cap.description,
                messages=rendered_msgs,
                untrusted=True
            )

        except MCPClientError as ce:
            raise ce
        except Exception as e:
            logger.error(f"Failed to render MCP prompt '{cap.name}': {e}")
            raise MCPValidationError(f"Failed to render prompt '{cap.name}': {str(e)}")
        finally:
            if client:
                await client.close()
