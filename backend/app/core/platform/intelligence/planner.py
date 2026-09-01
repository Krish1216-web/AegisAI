import uuid
from typing import Dict, Any, List, Optional, Set
from app.core.platform.context import PlatformContext
from app.core.platform.intelligence.models import (
    RequirementType,
    ExecutionMode,
    RequirementAnalysisResult,
    PlanStep,
    IntelligencePlan
)
from app.core.platform.intelligence.capability_selector import CapabilitySelector

MAX_INTELLIGENCE_STEPS = 12
MAX_PLAN_DEPTH = 6
MAX_PARALLEL_BRANCHES = 5

class IntelligencePlannerError(Exception):
    """Raised when an intelligence execution plan fails validation."""
    pass

class IntelligencePlanner:
    """
    Deterministic DAG execution plan generator for Phase 8.7 Advanced Intelligence.
    Builds sequential, parallel, and adaptive dependency graphs with strict depth and step limits.
    """

    @classmethod
    def create_plan(
        cls,
        context: PlatformContext,
        analysis: RequirementAnalysisResult,
        mode: ExecutionMode = ExecutionMode.ADAPTIVE,
        input_data: Dict[str, Any] = None
    ) -> IntelligencePlan:
        input_data = input_data or {}
        steps: List[PlanStep] = []
        step_counter = 1

        # 1. Step Construction for each identified requirement
        prev_step_ids: List[str] = []
        parallel_group_step_ids: List[str] = []

        for req in analysis.identified_requirements:
            cap_id = CapabilitySelector.select_best_for_requirement(context, req)
            if not cap_id:
                continue

            step_id = f"step_{step_counter}_{req.value}"
            fallback_id = None

            # Determine fallback
            if req == RequirementType.DOCUMENT_EVIDENCE:
                fallback_id = "knowledge.hybrid_rag" if cap_id == "knowledge.rag" else "rag.retriever"
            elif req == RequirementType.GRAPH_REASONING:
                fallback_id = "knowledge_graph.engine"

            # Input template generation
            template: Dict[str, Any] = {}
            if req == RequirementType.DOCUMENT_EVIDENCE:
                template = {
                    "query": analysis.query,
                    "top_k": input_data.get("top_k", 5),
                    "similarity_threshold": input_data.get("similarity_threshold", 0.0)
                }
            elif req == RequirementType.GRAPH_REASONING:
                entity = analysis.extracted_entities[0] if analysis.extracted_entities else input_data.get("entity", analysis.query)
                template = {
                    "entity": entity,
                    "depth": input_data.get("depth", 2)
                }
            elif req == RequirementType.MCP_TOOL:
                template = {
                    "tool_name": input_data.get("tool_name", "generic_tool"),
                    "arguments": input_data.get("arguments", {})
                }
            elif req == RequirementType.AGENT_REASONING:
                template = {
                    "query": analysis.query,
                    "model": input_data.get("model", "gpt-4o-mini")
                }
            elif req == RequirementType.WORKFLOW_EXECUTION:
                template = {
                    "workflow_id": input_data.get("workflow_id", "default_workflow"),
                    "input": input_data
                }
            elif req == RequirementType.MEMORY_CONTEXT:
                template = {
                    "key": input_data.get("memory_key", analysis.query)
                }

            # Dependencies based on mode
            dependencies: List[str] = []
            if mode == ExecutionMode.SEQUENTIAL:
                if prev_step_ids:
                    dependencies = [prev_step_ids[-1]]
            elif mode == ExecutionMode.PARALLEL:
                # Independent evidence steps (RAG, Graph, Memory) run in parallel with no dependencies
                if req in [RequirementType.DOCUMENT_EVIDENCE, RequirementType.GRAPH_REASONING, RequirementType.MEMORY_CONTEXT]:
                    dependencies = []
                    parallel_group_step_ids.append(step_id)
                elif req == RequirementType.AGENT_REASONING:
                    # Final synthesis depends on all parallel evidence gathering steps
                    dependencies = list(parallel_group_step_ids)
                else:
                    if prev_step_ids:
                        dependencies = [prev_step_ids[-1]]
            elif mode == ExecutionMode.ADAPTIVE:
                # In adaptive mode, evidence gathering is planned first, Agent synthesis runs after
                if req == RequirementType.AGENT_REASONING and prev_step_ids:
                    dependencies = list(prev_step_ids)
                elif prev_step_ids and req not in [RequirementType.DOCUMENT_EVIDENCE, RequirementType.GRAPH_REASONING]:
                    dependencies = [prev_step_ids[-1]]

            step = PlanStep(
                step_id=step_id,
                capability_id=cap_id,
                requirement_type=req,
                description=f"Execute {cap_id} to satisfy {req.value}",
                input_template=template,
                dependencies=dependencies,
                fallback_capability_id=fallback_id,
                timeout_seconds=input_data.get("step_timeout", 60),
                is_critical=True if req != RequirementType.MEMORY_CONTEXT else False
            )

            steps.append(step)
            prev_step_ids.append(step_id)
            step_counter += 1

        # Enforce step limit
        if len(steps) > MAX_INTELLIGENCE_STEPS:
            raise IntelligencePlannerError(
                f"Generated plan exceeds maximum allowed steps ({len(steps)} > {MAX_INTELLIGENCE_STEPS})"
            )

        # Plan validation & Depth Calculation
        depth = cls._calculate_plan_depth(steps)
        if depth > MAX_PLAN_DEPTH:
            raise IntelligencePlannerError(
                f"Plan depth ({depth}) exceeds maximum allowed depth ({MAX_PLAN_DEPTH})"
            )

        # Cycle validation
        cls._validate_acyclic(steps)

        return IntelligencePlan(
            mode=mode,
            steps=steps,
            max_depth=depth,
            total_steps=len(steps)
        )

    @classmethod
    def _calculate_plan_depth(cls, steps: List[PlanStep]) -> int:
        if not steps:
            return 0
        
        step_depths: Dict[str, int] = {}
        for step in steps:
            if not step.dependencies:
                step_depths[step.step_id] = 1
            else:
                max_parent = max((step_depths.get(dep, 1) for dep in step.dependencies), default=0)
                step_depths[step.step_id] = max_parent + 1

        return max(step_depths.values(), default=1)

    @classmethod
    def _validate_acyclic(cls, steps: List[PlanStep]) -> None:
        adj: Dict[str, List[str]] = {s.step_id: list(s.dependencies) for s in steps}
        
        # Self-loop check
        for step_id, deps in adj.items():
            if step_id in deps:
                raise IntelligencePlannerError(f"Self-loop cycle detected at step {step_id}")

        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            for dep in adj.get(node, []):
                if dep not in visited:
                    dfs(dep)
                elif dep in rec_stack:
                    raise IntelligencePlannerError(f"Cyclic dependency detected involving {node} -> {dep}")
            rec_stack.remove(node)

        for step in steps:
            if step.step_id not in visited:
                dfs(step.step_id)
