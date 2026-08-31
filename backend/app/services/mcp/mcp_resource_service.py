import uuid
import json
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from loguru import logger

from app.models.mcp import MCPServer, MCPCapability, MCPCapabilityType, MCPServerStatus
from app.core.mcp.base import (
    BaseMCPClient,
    MCPResourceContent,
    MCPClientError,
    MCPConnectionError,
    MCPValidationError,
    MCPTimeoutError
)
from app.core.mcp.connection import MCPConnectionManager
from app.core.mcp.validation import MCPValidator
from app.core.mcp.security import CredentialStore

MAX_RESOURCE_SIZE_BYTES = 1024 * 1024  # 1 MB

class MCPResourceService:
    """
    Service managing tenant-isolated MCP resource discovery, cataloging, URI validation,
    and safe content retrieval with caching and size bounds.
    """
    def __init__(self, db: Session, redis_client: Optional[Any] = None):
        self.db = db
        self.redis = redis_client

    def _get_resource_and_server(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID
    ) -> Tuple[MCPCapability, MCPServer]:
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
            raise MCPValidationError(f"MCP resource not found or access denied for ID: {resource_id}")

        return result

    def _format_resource(self, cap: MCPCapability, server: MCPServer) -> Dict[str, Any]:
        meta = cap.meta_data or {}
        input_sch = cap.input_schema or {}
        uri = input_sch.get("uri") or meta.get("uri") or f"resource://{cap.name}"
        mime_type = input_sch.get("mime_type") or meta.get("mime_type") or "text/plain"

        return {
            "id": cap.id,
            "server_id": server.id,
            "server_name": server.name,
            "server_transport": server.transport.value if hasattr(server.transport, "value") else str(server.transport),
            "server_status": server.status.value if hasattr(server.status, "value") else str(server.status),
            "server_enabled": server.enabled,
            "name": cap.name,
            "uri": uri,
            "mime_type": mime_type,
            "description": cap.description,
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

    def list_resources(
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
                MCPCapability.capability_type == MCPCapabilityType.RESOURCE,
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
        return [self._format_resource(cap, srv) for cap, srv in rows], total

    def get_resource(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        try:
            cap, server = self._get_resource_and_server(user_id, workspace_id, resource_id)
            return self._format_resource(cap, server)
        except MCPValidationError:
            return None

    def search_resources(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        query: str,
        server_id: Optional[uuid.UUID] = None,
        enabled_only: bool = False,
        include_stale: bool = True,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        resources, _ = self.list_resources(
            user_id=user_id,
            workspace_id=workspace_id,
            server_id=server_id,
            enabled_only=enabled_only,
            include_stale=include_stale,
            limit=100
        )

        if not query or not query.strip():
            return resources[:limit]

        q_lower = query.strip().lower()
        scored: List[Tuple[float, Dict[str, Any]]] = []

        for r in resources:
            score = 0.0
            r_name = r["name"].lower()
            r_uri = r["uri"].lower()
            r_desc = (r.get("description") or "").lower()

            if r_name == q_lower or r_uri == q_lower:
                score += 100.0
            elif r_name.startswith(q_lower):
                score += 80.0
            elif q_lower in r_name or q_lower in r_uri:
                score += 60.0
            elif q_lower in r_desc:
                score += 40.0

            if score > 0:
                scored.append((score, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    def toggle_resource(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID,
        enabled: bool
    ) -> Optional[Dict[str, Any]]:
        try:
            cap, server = self._get_resource_and_server(user_id, workspace_id, resource_id)
            cap.enabled = enabled
            self.db.commit()
            self.db.refresh(cap)
            return self._format_resource(cap, server)
        except MCPValidationError:
            return None

    async def read_resource(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID,
        timeout: float = 15.0
    ) -> MCPResourceContent:
        # Central Security Layer Check
        from app.services.mcp.mcp_security import MCPSecurityService, MCPSecurityDecisionEnum
        sec_service = MCPSecurityService(self.db, self.redis)
        decision = sec_service.evaluate_resource_read(user_id, workspace_id, resource_id)
        if decision.decision != MCPSecurityDecisionEnum.ALLOW:
            raise MCPValidationError(f"Cannot read resource: {decision.reason}")

        cap, server = self._get_resource_and_server(user_id, workspace_id, resource_id)

        # Extract and validate URI
        formatted = self._format_resource(cap, server)
        uri = formatted["uri"]
        valid_uri = MCPValidator.validate_resource_uri(uri)

        # Cache check
        cache_key = f"aegis:mcp:resource:{user_id}:{workspace_id}:{resource_id}:{cap.definition_hash}"
        if self.redis:
            try:
                cached = self.redis.get(cache_key)
                if cached:
                    cached_data = json.loads(cached)
                    return MCPResourceContent(**cached_data)
            except Exception:
                pass

        client: Optional[BaseMCPClient] = None
        try:
            client, _ = await MCPConnectionManager.connect_and_initialize(
                server_url=server.server_url,
                transport=server.transport,
                auth_config=server.auth_config,
                timeout=timeout
            )

            raw_res = await client.read_resource(valid_uri)
            
            raw_text = raw_res.get("text") or raw_res.get("content") or ""
            mime_type = raw_res.get("mime_type") or formatted["mime_type"] or "text/plain"

            # Check bounded size and truncate safely if needed
            content_bytes = raw_text.encode("utf-8")
            truncated = False
            if len(content_bytes) > MAX_RESOURCE_SIZE_BYTES:
                raw_text = content_bytes[:MAX_RESOURCE_SIZE_BYTES].decode("utf-8", errors="ignore")
                truncated = True

            res_content = MCPResourceContent(
                uri=valid_uri,
                mime_type=mime_type,
                text=raw_text,
                size=len(content_bytes),
                truncated=truncated,
                metadata={"server_name": server.name, "resource_name": cap.name}
            )

            # Cache in Redis with 300s TTL
            if self.redis:
                try:
                    self.redis.setex(cache_key, 300, res_content.model_dump_json())
                except Exception:
                    pass

            return res_content

        except MCPClientError as ce:
            raise ce
        except Exception as e:
            logger.error(f"Failed to read MCP resource '{cap.name}': {e}")
            raise MCPValidationError(f"Failed to read resource '{cap.name}': {str(e)}")
        finally:
            if client:
                await client.close()
