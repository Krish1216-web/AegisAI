import re
from typing import Dict, Any, List, Set
from app.core.platform.intelligence.models import (
    RequirementType,
    RequirementAnalysisResult
)

class RequirementAnalyzer:
    """
    Deterministic semantic and structural requirement analyzer for Phase 8.7.
    Extracts explicit and implicit capability requirements from user instructions.
    """

    # Keyword heuristics mapped to requirements
    DOC_KEYWORDS = {
        "document", "doc", "docs", "policy", "report", "article", "file", "text",
        "search", "find", "retrieve", "chunks", "manual", "guide", "pdf", "q3", "revenue"
    }

    GRAPH_KEYWORDS = {
        "graph", "entity", "entities", "relationship", "relationships", "connect",
        "connected", "node", "edge", "link", "hierarchy", "related to", "path", "network"
    }

    MCP_KEYWORDS = {
        "mcp", "tool", "server", "jira", "github", "slack", "database", "api",
        "fetch external", "execute tool", "calculator", "external service", "webhook"
    }

    AGENT_KEYWORDS = {
        "synthesize", "plan", "analyze", "explain", "summarize", "multi-agent",
        "reason", "evaluate", "compare", "recommend", "critique", "complex"
    }

    WORKFLOW_KEYWORDS = {
        "workflow", "pipeline", "dag", "schedule", "trigger", "step by step", "automation"
    }

    MEMORY_KEYWORDS = {
        "remember", "recall", "memory", "preference", "previous", "history", "last time"
    }

    @classmethod
    def analyze(cls, query: str, input_data: Dict[str, Any] = None) -> RequirementAnalysisResult:
        input_data = input_data or {}
        query_clean = (query or "").strip().lower()
        words = set(re.findall(r'\b\w+\b', query_clean))

        requirements: List[RequirementType] = []
        extracted_entities: List[str] = []

        # 1. Document / RAG Requirement Detection
        if any(kw in query_clean for kw in cls.DOC_KEYWORDS) or "document_id" in input_data or "top_k" in input_data:
            requirements.append(RequirementType.DOCUMENT_EVIDENCE)

        # 2. Knowledge Graph Requirement Detection
        if any(kw in query_clean for kw in cls.GRAPH_KEYWORDS) or "entity" in input_data or "depth" in input_data:
            requirements.append(RequirementType.GRAPH_REASONING)
            # Simple capitalized entity extraction from original query
            matches = re.findall(r'\b[A-Z][a-zA-Z0-9_-]+\b', query or "")
            for m in matches:
                if m.lower() not in {"what", "who", "where", "how", "when", "which", "the", "a", "an", "is"}:
                    extracted_entities.append(m)

        # 3. MCP External Tool Requirement Detection
        if any(kw in query_clean for kw in cls.MCP_KEYWORDS) or "tool_name" in input_data or "mcp_server" in input_data:
            requirements.append(RequirementType.MCP_TOOL)

        # 4. Workflow Requirement Detection
        if any(kw in query_clean for kw in cls.WORKFLOW_KEYWORDS) or "workflow_id" in input_data:
            requirements.append(RequirementType.WORKFLOW_EXECUTION)

        # 5. Memory Context Requirement Detection
        if any(kw in query_clean for kw in cls.MEMORY_KEYWORDS) or "memory_key" in input_data:
            requirements.append(RequirementType.MEMORY_CONTEXT)

        # 6. Multi-Agent Reasoning Detection (Default fallback or explicit synthesis)
        is_complex = len(requirements) >= 2 or any(kw in query_clean for kw in cls.AGENT_KEYWORDS) or len(words) > 15
        if is_complex or not requirements:
            requirements.append(RequirementType.AGENT_REASONING)

        # Remove duplicates while preserving order
        unique_reqs: List[RequirementType] = []
        for req in requirements:
            if req not in unique_reqs:
                unique_reqs.append(req)

        intent_desc = f"Identified {len(unique_reqs)} requirement(s): {', '.join([r.value for r in unique_reqs])}"

        return RequirementAnalysisResult(
            query=query,
            identified_requirements=unique_reqs,
            extracted_entities=list(set(extracted_entities)),
            intent_description=intent_desc,
            is_complex_synthesis=is_complex,
            requires_external_tool=RequirementType.MCP_TOOL in unique_reqs
        )
