import uuid
import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from loguru import logger

from app.models.mcp import MCPServer, MCPCapability, MCPCapabilityType, MCPServerStatus, MCPTransport
from app.core.mcp.policy import ToolRiskPolicy, ToolRiskLevel, ToolPolicyDecision
from app.core.mcp.base import MCPValidationError

class MCPToolCatalogService:
    """
    Dedicated service for workspace-wide MCP tool catalog queries, search, ranking,
    risk assessment, schema inspection, and execution readiness evaluation.
    """
    def __init__(self, db: Session):
        self.db = db

    def evaluate_execution_availability(
        self,
        server: MCPServer,
        capability: MCPCapability,
        risk_level: str
    ) -> bool:
        """
        Determines whether a tool capability is ready and valid for future execution.
        Must satisfy: server active & enabled, capability enabled & not stale, risk != invalid.
        """
        if not server or not capability:
            return False
        if not server.enabled or server.status != MCPServerStatus.ACTIVE:
            return False
        if not capability.enabled or capability.is_stale:
            return False
        if risk_level == ToolRiskLevel.INVALID.value:
            return False
        return True

    def _format_tool_item(self, capability: MCPCapability, server: MCPServer) -> Dict[str, Any]:
        risk = ToolRiskPolicy.assess_tool(
            name=capability.name,
            description=capability.description,
            input_schema=capability.input_schema,
            meta_data=capability.meta_data
        )
        is_available = self.evaluate_execution_availability(server, capability, risk["risk_level"])

        return {
            "id": capability.id,
            "server_id": server.id,
            "server_name": server.name,
            "server_transport": server.transport.value if hasattr(server.transport, "value") else str(server.transport),
            "server_status": server.status.value if hasattr(server.status, "value") else str(server.status),
            "server_enabled": server.enabled,
            "name": capability.name,
            "description": capability.description,
            "input_schema": capability.input_schema,
            "metadata": capability.meta_data,
            "enabled": capability.enabled,
            "is_stale": capability.is_stale,
            "stale_at": capability.stale_at,
            "definition_hash": capability.definition_hash,
            "version": capability.version,
            "risk_level": risk["risk_level"],
            "policy_decision": risk["policy_decision"],
            "risk_reasons": risk["risk_reasons"],
            "available_for_execution": is_available,
            "first_discovered_at": capability.first_discovered_at,
            "last_discovered_at": capability.last_discovered_at,
            "created_at": capability.created_at,
            "updated_at": capability.updated_at
        }

    def list_tools(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        server_id: Optional[uuid.UUID] = None,
        enabled_only: bool = False,
        include_stale: bool = True,
        risk_level: Optional[ToolRiskLevel] = None,
        transport: Optional[MCPTransport] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Lists all discovered tools across workspace MCP servers with multi-tenant isolation.
        """
        query = self.db.query(MCPCapability, MCPServer).join(
            MCPServer, MCPCapability.server_id == MCPServer.id
        ).filter(
            and_(
                MCPServer.user_id == user_id,
                MCPServer.workspace_id == workspace_id,
                MCPCapability.capability_type == MCPCapabilityType.TOOL,
                MCPCapability.deleted_at.is_(None),
                MCPServer.deleted_at.is_(None)
            )
        )

        if server_id:
            query = query.filter(MCPServer.id == server_id)
        if enabled_only:
            query = query.filter(MCPCapability.enabled.is_(True), MCPServer.enabled.is_(True))
        if not include_stale:
            query = query.filter(MCPCapability.is_stale.is_(False))
        if transport:
            query = query.filter(MCPServer.transport == transport)
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.filter(
                or_(
                    func.lower(MCPCapability.name).like(term),
                    func.lower(MCPCapability.description).like(term)
                )
            )

        total = query.count()
        results = query.order_by(MCPCapability.name.asc()).offset(offset).limit(limit).all()

        formatted_items = []
        for cap, srv in results:
            item = self._format_tool_item(cap, srv)
            if risk_level and item["risk_level"] != (risk_level.value if hasattr(risk_level, "value") else str(risk_level)):
                continue
            formatted_items.append(item)

        return formatted_items, total

    def get_tool(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        tool_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves detailed tool specification enforcing tenant workspace boundary.
        """
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
            return None

        cap, srv = result
        return self._format_tool_item(cap, srv)

    def search_tools(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        query: str,
        server_id: Optional[uuid.UUID] = None,
        risk_level: Optional[ToolRiskLevel] = None,
        enabled_only: bool = True,
        include_stale: bool = False,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Performs multi-tiered deterministic ranked search across the workspace tool catalog.
        Ranking Hierarchy:
          1. Exact name match (Score: 100)
          2. Prefix name match (Score: 80)
          3. Substring name match (Score: 60)
          4. Description keyword match (Score: 40)
          5. Fuzzy word match (Score: 20)
        """
        clean_q = (query or "").strip().lower()
        if not clean_q:
            tools, _ = self.list_tools(
                user_id=user_id,
                workspace_id=workspace_id,
                server_id=server_id,
                enabled_only=enabled_only,
                include_stale=include_stale,
                risk_level=risk_level,
                limit=limit
            )
            return tools

        base_query = self.db.query(MCPCapability, MCPServer).join(
            MCPServer, MCPCapability.server_id == MCPServer.id
        ).filter(
            and_(
                MCPServer.user_id == user_id,
                MCPServer.workspace_id == workspace_id,
                MCPCapability.capability_type == MCPCapabilityType.TOOL,
                MCPCapability.deleted_at.is_(None),
                MCPServer.deleted_at.is_(None)
            )
        )

        if server_id:
            base_query = base_query.filter(MCPServer.id == server_id)
        if enabled_only:
            base_query = base_query.filter(MCPCapability.enabled.is_(True), MCPServer.enabled.is_(True))
        if not include_stale:
            base_query = base_query.filter(MCPCapability.is_stale.is_(False))

        candidates = base_query.all()
        scored_items: List[Tuple[int, Dict[str, Any]]] = []

        for cap, srv in candidates:
            item = self._format_tool_item(cap, srv)
            if risk_level and item["risk_level"] != (risk_level.value if hasattr(risk_level, "value") else str(risk_level)):
                continue

            tool_name = (cap.name or "").lower()
            desc = (cap.description or "").lower()
            score = 0

            # 1. Exact Name Match
            if tool_name == clean_q:
                score += 100
            # 2. Prefix Match
            elif tool_name.startswith(clean_q):
                score += 80
            # 3. Substring Name Match
            elif clean_q in tool_name:
                score += 60
            # 4. Description Substring Match
            elif clean_q in desc:
                score += 40
            else:
                # 5. Word-by-word token matching
                tokens = clean_q.split()
                matches = sum(1 for t in tokens if t in tool_name or t in desc)
                if matches > 0:
                    score += 20 * (matches / len(tokens))

            if score > 0:
                scored_items.append((score, item))

        # Sort deterministically by descending score, then ascending tool name
        scored_items.sort(key=lambda x: (-x[0], x[1]["name"]))
        return [item for _, item in scored_items[:limit]]

    def toggle_tool(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        tool_id: uuid.UUID,
        enabled: bool
    ) -> Optional[Dict[str, Any]]:
        """
        Enables or disables an MCP tool capability without deleting it.
        """
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
            return None

        cap, srv = result
        cap.enabled = enabled
        cap.updated_at = datetime.datetime.now(datetime.timezone.utc)
        self.db.commit()
        self.db.refresh(cap)

        logger.info(f"Toggled MCP tool '{cap.name}' (ID: {cap.id}) enabled={enabled}")
        return self._format_tool_item(cap, srv)
