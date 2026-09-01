import uuid
import time
from typing import Dict, Any, List, Tuple, Optional
from loguru import logger

from app.core.platform.context import PlatformContext
from app.core.platform.provenance import (
    ProvenanceItem,
    ProvenanceSourceType,
    ProvenanceTrustLevel
)
from app.core.agent.state import AgentState, ExecutionStatus
from app.core.mcp.security import CredentialStore

class AgentContextBridge:
    """
    Bidirectional bridge mapping between PlatformContext and LangGraph AgentState.
    Guarantees strict tenant boundaries, immutable security context, and unified evidence provenance.
    """
    @staticmethod
    def platform_context_to_agent_state(
        context: PlatformContext,
        input_data: Dict[str, Any],
        provider: str = "mock",
        model: str = "gpt-4o-mini"
    ) -> AgentState:
        """
        Converts a PlatformContext and input payload into a validated AgentState.
        Enforces tenant isolation: input_data cannot override workspace_id or user_id.
        """
        prompt = input_data.get("query") or input_data.get("prompt") or input_data.get("task") or ""
        exec_id = str(uuid.uuid4())
        
        # Build clean initial state
        initial_state: AgentState = {
            "request_id": exec_id,
            "user_id": str(context.user_id),
            "workspace_id": str(context.workspace_id),
            "conversation_id": context.session_id or f"conv-{exec_id}",
            "original_prompt": str(prompt),
            "current_task": None,
            "execution_status": ExecutionStatus.PENDING,
            "execution_plan": None,
            "detailed_execution_plan": None,
            "messages": [],
            "agent_outputs": {},
            "tool_results": [],
            "memory_context": None,
            "memory_results": None,
            "rag_result": None,
            "rag_context": None,
            "rag_citations": [],
            "rag_confidence": None,
            "graph_context": None,
            "graph_citations": [],
            "mcp_servers": None,
            "mcp_capabilities": None,
            "mcp_tools_available": None,
            "mcp_execution_results": [],
            "mcp_resource_context": None,
            "mcp_prompt_context": None,
            "mcp_citations": [],
            "mcp_pending_confirmation": None,
            "research_results": None,
            "critic_result": None,
            "critic_decision": None,
            "quality_score": None,
            "final_response": None,
            "errors": [],
            "metadata": {
                "provider": input_data.get("provider", provider),
                "model": input_data.get("model", model),
                "correlation_id": context.correlation_id,
                "platform_execution_id": str(context.execution_id) if context.execution_id else None
            },
            "timestamps": {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")},
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "execution_time": 0.0,
            "confidence_score": 0.0,
            "current_agent": None,
            "retry_count": 0
        }
        return initial_state

    @staticmethod
    def agent_state_to_execution_output(
        state: AgentState,
        context: PlatformContext
    ) -> Tuple[Dict[str, Any], List[ProvenanceItem]]:
        """
        Transforms completed AgentState into Platform execution output dictionary and unified ProvenanceItem records.
        """
        output: Dict[str, Any] = {
            "response": state.get("final_response") or "Task completed with no final text synthesis.",
            "plan": state.get("execution_plan") or [],
            "critic_decision": state.get("critic_decision") or "APPROVED",
            "confidence_score": state.get("confidence_score", 1.0),
            "token_usage": state.get("token_usage", {}),
            "agent_outputs": CredentialStore.redact_sensitive_dict(state.get("agent_outputs", {})),
            "tool_results_count": len(state.get("tool_results", [])),
            "execution_time": state.get("execution_time", 0.0)
        }

        provenance_items: List[ProvenanceItem] = []

        # 1. RAG Citations
        for rag_cite in state.get("rag_citations", []):
            provenance_items.append(
                ProvenanceItem(
                    source_type=ProvenanceSourceType.DOCUMENT_CHUNK,
                    source_id=str(rag_cite.get("document_id") or rag_cite.get("chunk_id") or "rag_doc"),
                    uri=rag_cite.get("source_uri") or rag_cite.get("uri"),
                    title=rag_cite.get("document_title") or rag_cite.get("title") or "RAG Citation",
                    snippet=rag_cite.get("text_snippet") or rag_cite.get("snippet"),
                    trust_level=ProvenanceTrustLevel.VERIFIED_RAG,
                    confidence=float(rag_cite.get("relevance_score") or 0.9),
                    workspace_id=context.workspace_id,
                    metadata=rag_cite
                )
            )

        # 2. Knowledge Graph Citations
        for g_cite in state.get("graph_citations", []):
            provenance_items.append(
                ProvenanceItem(
                    source_type=ProvenanceSourceType.GRAPH_NODE,
                    source_id=str(g_cite.get("entity_id") or g_cite.get("node_id") or "kg_entity"),
                    title=g_cite.get("name") or g_cite.get("entity_name") or "KG Entity",
                    snippet=g_cite.get("description"),
                    trust_level=ProvenanceTrustLevel.VERIFIED_GRAPH,
                    confidence=float(g_cite.get("confidence") or 0.95),
                    workspace_id=context.workspace_id,
                    metadata=g_cite
                )
            )

        # 3. MCP Citations
        for mcp_cite in state.get("mcp_citations", []):
            provenance_items.append(
                ProvenanceItem(
                    source_type=ProvenanceSourceType.MCP_TOOL,
                    source_id=str(mcp_cite.get("tool_name") or "mcp_tool"),
                    title=f"MCP Tool: {mcp_cite.get('tool_name')}",
                    snippet=str(mcp_cite.get("result", "")),
                    trust_level=ProvenanceTrustLevel.UNTRUSTED_MCP,
                    workspace_id=context.workspace_id,
                    metadata=mcp_cite
                )
            )

        # 4. Agent Reasoning Provenance
        provenance_items.append(
            ProvenanceItem(
                source_type=ProvenanceSourceType.AGENT_REASONING,
                source_id="agent.orchestrator",
                title="LangGraph Multi-Agent Orchestrator",
                trust_level=ProvenanceTrustLevel.TRUSTED_INTERNAL,
                confidence=float(state.get("confidence_score", 1.0)),
                workspace_id=context.workspace_id,
                metadata={
                    "critic_decision": state.get("critic_decision"),
                    "plan_steps": len(state.get("execution_plan") or [])
                }
            )
        )

        return output, provenance_items
