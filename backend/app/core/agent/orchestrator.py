from enum import Enum
from typing import List, Dict, Any, Optional
import time
import json
from pydantic import BaseModel, Field
from loguru import logger

from app.core.agent.base import BaseAgent, AgentResult, ExecutionContext
from app.core.agent.state import AgentState, ExecutionStatus
from app.core.agent.prompts import ORCHESTRATOR_SYSTEM_PROMPT
from app.core.agent.exceptions import AgentValidationError, AgentExecutionError
from app.core.ai.base import ChatMessage
from app.services.ai_service import AIService

class TaskType(str, Enum):
    GENERAL_QA = "GENERAL_QA"
    RESEARCH = "RESEARCH"
    CODING = "CODING"
    DOCUMENT_ANALYSIS = "DOCUMENT_ANALYSIS"
    RAG_QUERY = "RAG_QUERY"
    GRAPH_QUERY = "GRAPH_QUERY"
    HYBRID_GRAPH_RAG = "HYBRID_GRAPH_RAG"
    DATA_ANALYSIS = "DATA_ANALYSIS"
    WORKFLOW_AUTOMATION = "WORKFLOW_AUTOMATION"
    MEMORY_QUERY = "MEMORY_QUERY"
    WEB_RESEARCH = "WEB_RESEARCH"
    FILE_OPERATION = "FILE_OPERATION"
    MIXED_TASK = "MIXED_TASK"
    UNKNOWN = "UNKNOWN"

class Complexity(str, Enum):
    SIMPLE = "SIMPLE"
    MODERATE = "MODERATE"
    COMPLEX = "COMPLEX"
    MULTI_STEP = "MULTI_STEP"

class AgentType(str, Enum):
    PLANNER = "PLANNER"
    RAG = "RAG"
    GRAPH = "GRAPH"
    RESEARCH = "RESEARCH"
    MEMORY = "MEMORY"
    TOOL_EXECUTOR = "TOOL_EXECUTOR"
    CRITIC = "CRITIC"
    RESPONSE_GENERATOR = "RESPONSE_GENERATOR"

class ExecutionPlan(BaseModel):
    task_type: TaskType
    complexity: Complexity
    goal: str
    steps: List[str]
    required_agents: List[AgentType]
    parallelizable_steps: List[int] = Field(default_factory=list)
    requires_memory: bool = False
    requires_graph: bool = False
    requires_rag: bool = False
    requires_research: bool = False
    requires_tools: bool = False
    requires_critic: bool = False
    requires_human_confirmation: bool = False
    requires_clarification: bool = False
    clarification_question: Optional[str] = None
    confidence: float

class OrchestratorAgent(BaseAgent):
    """
    Central Orchestrator analyzing requests and formulating execution plans.
    """
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service

    @property
    def name(self) -> str:
        return "OrchestratorAgent"

    @property
    def description(self) -> str:
        return "Analyzes user requests to perform classification, planning, and capabilities orchestration."

    def validate_input(self, state: AgentState) -> bool:
        if not state.get("original_prompt") and len(state.get("messages", [])) == 0:
            return False
        return True

    def validate_output(self, result: AgentResult) -> bool:
        if not result.output:
            return False
        return True

    def health_check(self) -> bool:
        return True

    async def execute(self, state: AgentState, context: ExecutionContext) -> AgentResult:
        logger.info(f"Orchestrator executing prompt: {state.get('original_prompt')}")
        start_time = time.perf_counter()
        
        # Resolve prompt content
        prompt = state.get("original_prompt") or ""
        if not prompt and state.get("messages"):
            prompt = state["messages"][-1]["content"]

        # Support Mock mode execution to bypass API key requirement in local tests
        if context.provider == "mock" or "mock" in prompt.lower():
            logger.info("Executing Orchestrator in Mock mode.")
            lowered = prompt.lower()
            requires_tools = "calculate" in lowered or "weather" in lowered
            requires_research = "research" in lowered or "industry" in lowered or "latest" in lowered
            requires_memory = "context" in lowered or "calculate" in lowered or "preference" in lowered or "previous" in lowered
            requires_graph = any(kw in lowered for kw in ["graph", "related", "depend", "connected", "relationship", "path", "topology", "link", "hub", "chain"])
            requires_rag = any(kw in lowered for kw in ["report", "document", "contract", "rag", "uploaded", "paper", "pdf", "docx", "file"])
            
            required_agents = [AgentType.RESPONSE_GENERATOR]
            if requires_memory:
                required_agents.append(AgentType.MEMORY)
            if requires_graph:
                required_agents.append(AgentType.GRAPH)
            if requires_rag:
                required_agents.append(AgentType.RAG)
            if requires_research:
                required_agents.append(AgentType.RESEARCH)
            if requires_tools:
                required_agents.append(AgentType.TOOL_EXECUTOR)

            task_type = TaskType.GENERAL_QA
            if requires_graph and requires_rag:
                task_type = TaskType.HYBRID_GRAPH_RAG
            elif requires_graph:
                task_type = TaskType.GRAPH_QUERY
            elif requires_rag and requires_research:
                task_type = TaskType.MIXED_TASK
            elif requires_rag:
                task_type = TaskType.DOCUMENT_ANALYSIS
            elif requires_research:
                task_type = TaskType.RESEARCH
            elif requires_memory:
                task_type = TaskType.MEMORY_QUERY

            mock_plan = ExecutionPlan(
                task_type=task_type,
                complexity=Complexity.SIMPLE if len(required_agents) <= 2 else Complexity.MODERATE,
                goal=f"Processed plan for: {prompt[:40]}",
                steps=["Execute mapped plan nodes"],
                required_agents=required_agents,
                requires_memory=requires_memory,
                requires_graph=requires_graph,
                requires_rag=requires_rag,
                requires_research=requires_research,
                requires_tools=requires_tools,
                confidence=0.99
            )
            elapsed = time.perf_counter() - start_time
            return AgentResult(
                agent_name=self.name,
                status="success",
                output=mock_plan.model_dump_json(),
                confidence=0.99,
                execution_time=elapsed,
                token_usage={"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25}
            )

        # Execute through active AI Service
        messages = [
            ChatMessage(role="system", content=ORCHESTRATOR_SYSTEM_PROMPT),
            ChatMessage(role="user", content=prompt)
        ]
        
        try:
            response = await self.ai_service.generate_chat(
                messages=messages,
                provider=context.provider,
                model=context.model,
                user_id=context.user_id
            )
            
            # Sanitize response text
            raw_text = response.content.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text.replace("```json", "", 1)
            if raw_text.endswith("```"):
                raw_text = raw_text.rsplit("```", 1)[0]
            raw_text = raw_text.strip()
            
            # Validation parse
            plan = ExecutionPlan.model_validate_json(raw_text)
            elapsed = time.perf_counter() - start_time
            
            return AgentResult(
                agent_name=self.name,
                status="success",
                output=plan.model_dump_json(),
                confidence=plan.confidence,
                execution_time=elapsed,
                token_usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            )
        except Exception as e:
            logger.error(f"Orchestrator model execution failed: {e}")
            raise AgentExecutionError(f"Model failed to generate structured plan: {e}")

def route_orchestrator(state: AgentState) -> str:
    """
    LangGraph conditional router checking the orchestrator output status.
    """
    agent_outputs = state.get("agent_outputs", {})
    orch_output = agent_outputs.get("OrchestratorAgent")
    
    if not orch_output:
        logger.warning("Orchestrator output not found in state, ending graph run.")
        return "END"
        
    try:
        plan_data = json.loads(orch_output["output"])
        plan = ExecutionPlan(**plan_data)
        
        if plan.requires_clarification:
            logger.info("Orchestrator requires clarification. Routing to END.")
            return "END"
            
        return "PlannerAgent"
    except Exception as e:
        logger.error(f"Failed to route orchestrator output: {e}")
        return "END"
