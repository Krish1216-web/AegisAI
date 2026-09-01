from typing import Dict, Any, List, Optional
from app.core.platform.context import PlatformContext
from app.core.platform.capability import CapabilityType, platform_capability_registry
from app.core.platform.intelligence.models import (
    RequirementType,
    RequirementAnalysisResult,
    CapabilityScore
)

class CapabilitySelector:
    """
    Deterministic capability scoring and selection engine for Phase 8.7.
    Scores and ranks available platform capabilities against analyzed requirements.
    """

    REQUIREMENT_TO_CAPABILITY_TYPE = {
        RequirementType.DOCUMENT_EVIDENCE: [CapabilityType.RAG],
        RequirementType.GRAPH_REASONING: [CapabilityType.KNOWLEDGE_GRAPH],
        RequirementType.MCP_TOOL: [CapabilityType.MCP],
        RequirementType.MCP_RESOURCE: [CapabilityType.MCP],
        RequirementType.AGENT_REASONING: [CapabilityType.AGENT, CapabilityType.REASONING],
        RequirementType.WORKFLOW_EXECUTION: [CapabilityType.WORKFLOW],
        RequirementType.MEMORY_CONTEXT: [CapabilityType.MEMORY]
    }

    # Deterministic preferred capabilities by requirement
    PREFERRED_CAPABILITY_IDS = {
        RequirementType.DOCUMENT_EVIDENCE: "knowledge.rag",
        RequirementType.GRAPH_REASONING: "knowledge.graph",
        RequirementType.MCP_TOOL: "mcp.tool",
        RequirementType.MCP_RESOURCE: "mcp.resource",
        RequirementType.AGENT_REASONING: "agent.orchestrator",
        RequirementType.WORKFLOW_EXECUTION: "workflow.engine",
        RequirementType.MEMORY_CONTEXT: "memory.manager"
    }

    @classmethod
    def _ensure_initialized(cls, context: PlatformContext) -> None:
        if len(platform_capability_registry.list_available(context.workspace_id, context.security_context.user_role)) == 0:
            from app.services.platform_service import PlatformService
            PlatformService(None)

    @classmethod
    def score_capabilities(
        cls,
        context: PlatformContext,
        analysis: RequirementAnalysisResult
    ) -> List[CapabilityScore]:
        cls._ensure_initialized(context)
        available_caps = platform_capability_registry.list_available(
            workspace_id=context.workspace_id,
            user_role=context.security_context.user_role
        )

        scores: List[CapabilityScore] = []

        for cap in available_caps:
            score = 0.0
            reasons: List[str] = []
            is_eligible = True

            # 1. Enabled check
            if not cap.enabled:
                is_eligible = False
                reasons.append("Capability disabled")

            # 2. Permission check
            if cap.required_permissions:
                has_perms = all(context.security_context.has_permission(p) for p in cap.required_permissions)
                if not has_perms:
                    is_eligible = False
                    reasons.append(f"Missing required permissions: {list(cap.required_permissions)}")

            if not is_eligible:
                scores.append(CapabilityScore(
                    capability_id=cap.capability_id,
                    capability_type=cap.capability_type.value,
                    score=-1.0,
                    is_eligible=False,
                    reasons=reasons
                ))
                continue

            # 3. Requirement Type Match (+4.0)
            for req in analysis.identified_requirements:
                matching_types = cls.REQUIREMENT_TO_CAPABILITY_TYPE.get(req, [])
                if cap.capability_type in matching_types:
                    score += 4.0
                    reasons.append(f"Matches requirement {req.value} (+4.0)")

                # Preferred capability bonus (+2.0)
                if cap.capability_id == cls.PREFERRED_CAPABILITY_IDS.get(req):
                    score += 2.0
                    reasons.append("Preferred capability for requirement (+2.0)")

            # 4. Tag / Keyword Match (+1.0 per tag match)
            if cap.tags:
                query_words = set(analysis.query.lower().split())
                matched_tags = [t for t in cap.tags if t.lower() in query_words]
                if matched_tags:
                    score += min(len(matched_tags) * 0.5, 2.0)
                    reasons.append(f"Tag matches: {matched_tags} (+{min(len(matched_tags) * 0.5, 2.0)})")

            # 5. Base reliability & execution readiness (+1.0)
            score += 1.0

            scores.append(CapabilityScore(
                capability_id=cap.capability_id,
                capability_type=cap.capability_type.value,
                score=round(score, 3),
                is_eligible=True,
                reasons=reasons
            ))

        # Deterministic sorting: highest score first, then stable alphabetical sort on capability_id
        scores.sort(key=lambda s: (-s.score, s.capability_id))
        return scores

    @classmethod
    def select_best_for_requirement(
        cls,
        context: PlatformContext,
        requirement: RequirementType
    ) -> Optional[str]:
        """Returns the single best available capability ID for a given requirement."""
        cls._ensure_initialized(context)
        matching_types = cls.REQUIREMENT_TO_CAPABILITY_TYPE.get(requirement, [])
        preferred_id = cls.PREFERRED_CAPABILITY_IDS.get(requirement)

        available_caps = platform_capability_registry.list_available(
            workspace_id=context.workspace_id,
            user_role=context.security_context.user_role
        )

        eligible_map = {c.capability_id: c for c in available_caps if c.enabled}

        if preferred_id and preferred_id in eligible_map:
            cap = eligible_map[preferred_id]
            if not cap.required_permissions or context.security_context.has_all_permissions(list(cap.required_permissions)):
                return preferred_id

        # Fallback to any eligible matching type
        for cap_id, cap in eligible_map.items():
            if cap.capability_type in matching_types:
                if not cap.required_permissions or context.security_context.has_all_permissions(list(cap.required_permissions)):
                    return cap_id

        return None
