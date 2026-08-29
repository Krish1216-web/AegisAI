from typing import List, Dict, Any, Optional, Set
import time
import json
from pydantic import BaseModel, Field
from loguru import logger

from app.core.agent.base import BaseAgent, AgentResult, ExecutionContext
from app.core.agent.state import AgentState, ExecutionStatus
from app.core.agent.prompts import PLANNER_SYSTEM_PROMPT
from app.core.agent.exceptions import AgentValidationError, AgentExecutionError
from app.core.agent.orchestrator import AgentType, TaskType, Complexity, ExecutionPlan
from app.core.ai.base import ChatMessage
from app.services.ai_service import AIService

class PlanStep(BaseModel):
    step_id: str
    title: str
    description: str
    agent_type: AgentType
    action: str
    inputs: List[str] = Field(default_factory=list)
    expected_output: str
    dependencies: List[str] = Field(default_factory=list)
    priority: int = 1
    estimated_duration: float = 0.0
    can_run_parallel: bool = False
    requires_confirmation: bool = False

class DetailedExecutionPlan(BaseModel):
    steps: List[PlanStep]

# Configurable plan validation parameters
MAX_PLAN_STEPS = 15
MAX_DEPENDENCY_DEPTH = 5
MAX_PARALLEL_STEPS = 8

class PlannerAgent(BaseAgent):
    """
    PlannerAgent decomposes Orchestrator goals into step-by-step dependency plans.
    """
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service

    @property
    def name(self) -> str:
        return "PlannerAgent"

    @property
    def description(self) -> str:
        return "Converts high-level Orchestrator goals into dependency-aware executable steps."

    def validate_input(self, state: AgentState) -> bool:
        # Require orchestrator plan output to plan details
        agent_outputs = state.get("agent_outputs", {})
        if "OrchestratorAgent" not in agent_outputs:
            return False
        return True

    def validate_output(self, result: AgentResult) -> bool:
        if not result.output:
            return False
        return True

    def health_check(self) -> bool:
        return True

    def _detect_circular_dependencies(self, steps: List[PlanStep]) -> bool:
        adj = {step.step_id: step.dependencies for step in steps}
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str) -> bool:
            if node in rec_stack:
                return True
            if node in visited:
                return False
            rec_stack.add(node)
            for neighbor in adj.get(node, []):
                if dfs(neighbor):
                    return True
            rec_stack.remove(node)
            visited.add(node)
            return False

        for step in steps:
            if dfs(step.step_id):
                return True
        return False

    def validate_plan_schema(self, plan: DetailedExecutionPlan):
        steps = plan.steps
        
        # 1. Size limits checks
        if len(steps) > MAX_PLAN_STEPS:
            raise AgentValidationError(f"Plan size exceeds maximum step limit: {MAX_PLAN_STEPS}")

        step_ids = [s.step_id for s in steps]
        
        # 2. Duplicate Step IDs
        if len(step_ids) != len(set(step_ids)):
            raise AgentValidationError("Plan contains duplicate step IDs.")

        # 3. Validation of Dependency References
        for step in steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    raise AgentValidationError(f"Step {step.step_id} depends on non-existent step: {dep}")

        # 4. Circular Dependency Checks
        if self._detect_circular_dependencies(steps):
            raise AgentValidationError("Circular dependencies detected in execution plan.")

    async def execute(self, state: AgentState, context: ExecutionContext) -> AgentResult:
        logger.info("Planner Agent parsing orchestrator high-level goals.")
        start_time = time.perf_counter()
        
        # Resolve Orchestrator output
        orch_raw = state["agent_outputs"]["OrchestratorAgent"]["output"]
        
        # Extract user permissions and context
        permissions = context.permissions
        
        # Mock mode check
        if context.provider == "mock" or "mock" in state.get("original_prompt", "").lower():
            logger.info("Executing Planner in Mock mode.")
            steps = []
            step_idx = 1
            
            try:
                orch_plan = ExecutionPlan.model_validate_json(orch_raw)
                if orch_plan.requires_memory:
                    steps.append(
                        PlanStep(
                            step_id=f"step_{step_idx}",
                            title="Memory Retrieval",
                            description="Retrieve relevant user preferences and past context",
                            agent_type=AgentType.MEMORY,
                            action="query_memory",
                            expected_output="User context string",
                            can_run_parallel=True
                        )
                    )
                    step_idx += 1
                if orch_plan.requires_rag:
                    steps.append(
                        PlanStep(
                            step_id=f"step_{step_idx}",
                            title="Document RAG Retrieval",
                            description="Retrieve relevant workspace document chunks and grounded context",
                            agent_type=AgentType.RAG,
                            action="retrieve_and_answer",
                            expected_output="Grounded answer with verified citations",
                            can_run_parallel=True
                        )
                    )
                    step_idx += 1
                if orch_plan.requires_research:
                    steps.append(
                        PlanStep(
                            step_id=f"step_{step_idx}",
                            title="Web Research",
                            description="Search live sources for current factual information",
                            agent_type=AgentType.RESEARCH,
                            action="search_web",
                            expected_output="Structured research findings with citations",
                            can_run_parallel=True
                        )
                    )
                    step_idx += 1
                if orch_plan.requires_tools:
                    steps.append(
                        PlanStep(
                            step_id=f"step_{step_idx}",
                            title="Tool Execution",
                            description="Run required computation or helper tools",
                            agent_type=AgentType.TOOL_EXECUTOR,
                            action="calculator",
                            expected_output="Calculation result"
                        )
                    )
                    step_idx += 1
            except Exception:
                pass

            if not steps:
                steps.append(
                    PlanStep(
                        step_id="step_1",
                        title="Generate Response",
                        description="Formulate final grounded response",
                        agent_type=AgentType.RESPONSE_GENERATOR,
                        action="generate_reply",
                        expected_output="Final synthesized response"
                    )
                )

            mock_plan = DetailedExecutionPlan(steps=steps)
            elapsed = time.perf_counter() - start_time
            return AgentResult(
                agent_name=self.name,
                status="success",
                output=mock_plan.model_dump_json(),
                confidence=0.99,
                execution_time=elapsed,
                token_usage={"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25}
            )

        messages = [
            ChatMessage(role="system", content=PLANNER_SYSTEM_PROMPT),
            ChatMessage(role="user", content=f"Goal details: {orch_raw}. Available permissions: {permissions}")
        ]

        try:
            response = await self.ai_service.generate_chat(
                messages=messages,
                provider=context.provider,
                model=context.model,
                user_id=context.user_id
            )

            raw_text = response.content.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text.replace("```json", "", 1)
            if raw_text.endswith("```"):
                raw_text = raw_text.rsplit("```", 1)[0]
            raw_text = raw_text.strip()

            plan = DetailedExecutionPlan.model_validate_json(raw_text)
            
            # Run topological validations
            self.validate_plan_schema(plan)

            # Enforce permission checks: check if any step uses restricted tools/agents
            for step in plan.steps:
                if step.action.startswith("github_") and "github" not in permissions:
                    raise AgentValidationError(f"Permission denied for scheduled action: {step.action}")

            elapsed = time.perf_counter() - start_time
            return AgentResult(
                agent_name=self.name,
                status="success",
                output=plan.model_dump_json(),
                confidence=0.95,
                execution_time=elapsed,
                token_usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            )
        except AgentValidationError as e:
            raise e
        except Exception as e:
            logger.error(f"Planner execution failure: {e}")
            raise AgentExecutionError(f"Planner failed to generate executable steps: {e}")
