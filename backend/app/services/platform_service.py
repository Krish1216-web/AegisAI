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
                capability_id="knowledge.rag",
                capability_type=CapabilityType.RAG,
                name="Cognitive RAG Pipeline",
                description="Vector similarity retrieval with cosine distance, reranking, and citation verification.",
                version="1.0.0",
                enabled=True,
                input_schema={
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string", "description": "Search query or question"},
                        "top_k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 50},
                        "similarity_threshold": {"type": "number", "default": 0.0, "minimum": 0.0, "maximum": 1.0},
                        "rerank": {"type": "boolean", "default": True},
                        "metadata_filters": {"type": "object"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "answer": {"type": "string"},
                        "chunks_count": {"type": "integer"},
                        "chunks": {"type": "array"},
                        "citations": {"type": "array"}
                    }
                },
                tags=["rag", "embeddings", "vector", "citations"]
            ),
            CapabilityMetadata(
                capability_id="knowledge.hybrid_rag",
                capability_type=CapabilityType.RAG,
                name="Hybrid Graph + Vector RAG Engine",
                description="Unified retrieval fusing vector similarity search with Knowledge Graph multi-hop entity traversal.",
                version="1.0.0",
                enabled=True,
                input_schema={
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string", "description": "Hybrid search query"},
                        "top_k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 50},
                        "include_graph": {"type": "boolean", "default": True},
                        "graph_depth": {"type": "integer", "default": 2, "minimum": 1, "maximum": 5}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "answer": {"type": "string"},
                        "document_evidence": {"type": "array"},
                        "graph_evidence": {"type": "array"},
                        "relationships": {"type": "array"},
                        "confidence_score": {"type": "number"}
                    }
                },
                tags=["hybrid", "rag", "graph", "fusion", "evidence"]
            ),
            CapabilityMetadata(
                capability_id="knowledge.graph",
                capability_type=CapabilityType.KNOWLEDGE_GRAPH,
                name="Knowledge Graph Intelligence",
                description="Entity resolution, relationship extraction, neighborhood traversal, and path analytics.",
                version="1.0.0",
                enabled=True,
                input_schema={
                    "type": "object",
                    "required": ["entity"],
                    "properties": {
                        "entity": {"type": "string", "description": "Entity name or node ID to explore"},
                        "depth": {"type": "integer", "default": 2, "minimum": 1, "maximum": 5}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "nodes_count": {"type": "integer"},
                        "edges_count": {"type": "integer"},
                        "nodes": {"type": "array"},
                        "edges": {"type": "array"},
                        "paths": {"type": "array"}
                    }
                },
                tags=["graph", "entities", "relationships", "intelligence"]
            ),
            CapabilityMetadata(
                capability_id="rag.retriever",
                capability_type=CapabilityType.RAG,
                name="Cognitive RAG Pipeline (Legacy Alias)",
                description="Vector retrieval with cosine similarity, reranking, and citation verification.",
                version="1.0.0",
                enabled=True,
                tags=["rag", "embeddings", "citations"]
            ),
            CapabilityMetadata(
                capability_id="knowledge_graph.engine",
                capability_type=CapabilityType.KNOWLEDGE_GRAPH,
                name="Knowledge Graph Intelligence (Legacy Alias)",
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
                capability_id="mcp.tool",
                capability_type=CapabilityType.MCP,
                name="MCP Tool Execution",
                description="Deterministic execution of external Model Context Protocol tools with risk gating and single-use confirmation.",
                version="1.0.0",
                enabled=True,
                input_schema={
                    "type": "object",
                    "required": ["tool_name"],
                    "properties": {
                        "tool_name": {"type": "string", "description": "Name or identifier of the MCP tool"},
                        "arguments": {"type": "object", "description": "JSON arguments payload"},
                        "confirmation_token": {"type": "string", "description": "Single-use cryptographic confirmation token"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string"},
                        "server_id": {"type": "string"},
                        "output": {"type": "object"},
                        "status": {"type": "string"},
                        "confirmation_required": {"type": "boolean"},
                        "confirmation_token": {"type": "string"}
                    }
                },
                tags=["mcp", "tool", "executor", "risk_policy", "confirmation"]
            ),
            CapabilityMetadata(
                capability_id="mcp.resource",
                capability_type=CapabilityType.MCP,
                name="MCP Resource Provider",
                description="Secure reading of external MCP resources with SSRF protection, size bounds, and untrusted data isolation.",
                version="1.0.0",
                enabled=True,
                input_schema={
                    "type": "object",
                    "properties": {
                        "resource_id": {"type": "string", "description": "Resource identifier"},
                        "uri": {"type": "string", "description": "Resource URI"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "resource_uri": {"type": "string"},
                        "server_id": {"type": "string"},
                        "content": {"type": "string"},
                        "truncated": {"type": "boolean"}
                    }
                },
                tags=["mcp", "resource", "reader", "ssrf_protection"]
            ),
            CapabilityMetadata(
                capability_id="mcp.prompt",
                capability_type=CapabilityType.MCP,
                name="MCP Prompt Template Engine",
                description="Rendering of external MCP prompt templates with argument validation and injection protection.",
                version="1.0.0",
                enabled=True,
                input_schema={
                    "type": "object",
                    "required": ["prompt_name"],
                    "properties": {
                        "prompt_name": {"type": "string", "description": "Name of the prompt template"},
                        "arguments": {"type": "object", "description": "Template variables map"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "prompt_name": {"type": "string"},
                        "server_id": {"type": "string"},
                        "messages": {"type": "array"}
                    }
                },
                tags=["mcp", "prompt", "template", "rendering"]
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
            ),
            CapabilityMetadata(
                capability_id="intelligence.orchestrator",
                capability_type=CapabilityType.INTELLIGENCE,
                name="Adaptive Intelligence & Orchestration",
                description="Deterministic intent analysis, DAG planning, and adaptive multi-capability execution.",
                version="1.0.0",
                enabled=True,
                input_schema={
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string", "description": "Natural language query or task instruction"},
                        "mode": {"type": "string", "enum": ["sequential", "parallel", "adaptive"], "default": "adaptive"},
                        "confidence_threshold": {"type": "number", "default": 0.60}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "response": {"type": "string"},
                        "plan": {"type": "object"},
                        "decisions": {"type": "array"},
                        "evidence_evaluation": {"type": "object"},
                        "confidence": {"type": "number"}
                    }
                },
                tags=["intelligence", "adaptive", "planner", "orchestrator", "dag"]
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
