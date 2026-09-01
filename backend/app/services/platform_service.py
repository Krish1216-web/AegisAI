import uuid
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.orm import Session

from app.core.platform.capability import (
    CapabilityType,
    CapabilityMetadata,
    PlatformCapability,
    platform_capability_registry
)
from app.core.platform.config import get_platform_settings
from app.schemas.platform import PlatformStatusResponse, PlatformCapabilityListResponse

class ConcretePlatformCapability(PlatformCapability):
    """Generic capability wrapper for platform services."""
    pass

class PlatformService:
    """
    Service layer for Phase 8 Advanced Platform discovery, status, and governance.
    """
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_platform_settings()
        self._ensure_default_capabilities_registered()

    def _ensure_default_capabilities_registered(self) -> None:
        """Registers verified platform capabilities into the global registry."""
        default_caps = [
            CapabilityMetadata(
                capability_id="agent.orchestrator",
                capability_type=CapabilityType.AGENT,
                name="Multi-Agent Orchestrator",
                description="Deterministic LangGraph multi-agent cognitive pipeline orchestrating Planner, Tool Executor, Critic, and Response Generator.",
                version="1.0.0",
                enabled=True,
                input_schema={
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string", "description": "User prompt or task instruction"},
                        "provider": {"type": "string", "default": "openai"},
                        "model": {"type": "string", "default": "gpt-4o-mini"},
                        "session_id": {"type": "string"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "response": {"type": "string"},
                        "plan": {"type": "array"},
                        "critic_decision": {"type": "string"},
                        "confidence_score": {"type": "number"}
                    }
                },
                tags=["agent", "planner", "critic", "executor", "langgraph"]
            ),
            CapabilityMetadata(
                capability_id="rag.retriever",
                capability_type=CapabilityType.RAG,
                name="Cognitive RAG Pipeline",
                description="Vector retrieval with cosine similarity, reranking, and citation verification.",
                version="1.0.0",
                enabled=True,
                tags=["rag", "embeddings", "citations"]
            ),
            CapabilityMetadata(
                capability_id="knowledge_graph.engine",
                capability_type=CapabilityType.KNOWLEDGE_GRAPH,
                name="Knowledge Graph Intelligence",
                description="Entity resolution, relationship extraction, and graph traversal analytics.",
                version="1.0.0",
                enabled=True,
                tags=["graph", "entities", "relationships"]
            ),
            CapabilityMetadata(
                capability_id="memory.manager",
                capability_type=CapabilityType.MEMORY,
                name="Long-Term Memory Store",
                description="Tenant-isolated episodic and semantic memory management with sync hooks.",
                version="1.0.0",
                enabled=True,
                tags=["memory", "facts", "recall"]
            ),
            CapabilityMetadata(
                capability_id="mcp.platform",
                capability_type=CapabilityType.MCP,
                name="Model Context Protocol Platform",
                description="MCP Server registry, tool discovery, resource prompts, and risk-gated execution.",
                version="1.0.0",
                enabled=True,
                tags=["mcp", "tools", "servers", "prompts"]
            ),
            CapabilityMetadata(
                capability_id="workflow.engine",
                capability_type=CapabilityType.WORKFLOW,
                name="Visual Workflow & Composition Engine",
                description="DAG execution, branching, human approval, cron scheduling, and sub-workflows.",
                version="1.0.0",
                enabled=True,
                tags=["workflow", "dag", "parallel", "approvals", "cron"]
            )
        ]

        for cap_meta in default_caps:
            if not platform_capability_registry.get(cap_meta.capability_id):
                platform_capability_registry.register(ConcretePlatformCapability(cap_meta))

    def get_platform_status(self, workspace_id: uuid.UUID) -> PlatformStatusResponse:
        """Returns overall Phase 8 platform status for the workspace."""
        caps = platform_capability_registry.list_available(workspace_id, user_role="admin")
        return PlatformStatusResponse(
            version="8.1.0",
            phase="Phase 8: Advanced Platform",
            workspace_id=workspace_id,
            active_capabilities=len(caps),
            system_health="HEALTHY",
            feature_flags=self.settings.feature_flags,
            registered_subsystems=[c.name for c in caps]
        )

    def list_capabilities(
        self,
        workspace_id: uuid.UUID,
        user_role: str = "viewer",
        user_permissions: Optional[Set[str]] = None,
        capability_type: Optional[CapabilityType] = None
    ) -> PlatformCapabilityListResponse:
        """Returns capabilities filtered by workspace boundary and caller permissions."""
        items = platform_capability_registry.list_available(
            workspace_id=workspace_id,
            user_role=user_role,
            user_permissions=user_permissions,
            capability_type=capability_type
        )
        return PlatformCapabilityListResponse(
            total=len(items),
            items=items,
            workspace_id=workspace_id
        )

    def get_capability(
        self,
        workspace_id: uuid.UUID,
        capability_id: str,
        user_role: str = "viewer",
        user_permissions: Optional[Set[str]] = None
    ) -> Optional[CapabilityMetadata]:
        """Retrieves a single capability ensuring tenant access."""
        cap = platform_capability_registry.get(capability_id)
        if not cap:
            return None
        perms = user_permissions or set()
        if not cap.is_accessible_by(workspace_id, user_role, perms):
            return None
        return cap.metadata
