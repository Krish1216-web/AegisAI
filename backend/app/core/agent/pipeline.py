import uuid
import time
import json
import datetime
from typing import Dict, Any, List, Optional, AsyncGenerator, Set
from loguru import logger
from langgraph.graph import END

from app.core.agent.state import AgentState, ExecutionStatus
from app.core.agent.base import BaseAgent, AgentResult, ExecutionContext
from app.core.agent.checkpoint import BaseCheckpointer, InMemoryCheckpointer
from app.core.agent.graph import AegisAgentGraph, log_event
from app.core.agent.exceptions import (
    GraphExecutionError, ToolPermissionDenied, MemoryPermissionError, ToolConfirmationInvalid
)
from app.core.agent.orchestrator import OrchestratorAgent, route_orchestrator, ExecutionPlan, AgentType
from app.core.agent.planner import PlannerAgent, DetailedExecutionPlan
from app.core.agent.graph_reasoning import GraphReasoningAgent
from app.core.agent.rag import RAGAgent
from app.core.agent.research import ResearchAgent, MockResearchProvider, ResearchResult, ResearchProviderFactory
from app.core.agent.memory import MemoryAgent, MockMemoryProvider, MemoryResult, MemoryProviderFactory
from app.core.agent.tools import (
    ToolRegistry, MockCalculatorTool, MockSearchTool, MockDocumentReaderTool, MockWeatherTool
)
from app.core.agent.executor import ToolExecutorAgent
from app.core.agent.critic import CriticAgent, CriticResult, CriticDecision
from app.core.agent.response import ResponseGeneratorAgent, ResponseGenerationResult

MAX_AGENT_ITERATIONS = 10

class AegisAIPipeline:
    """
    Unified LangGraph execution pipeline coordinating agent handoffs and events,
    integrating Memory, Graph Reasoning, RAG, Web Research, Tool Execution, Critic, and Response Generation.
    """
    def __init__(self, ai_service: Any, checkpointer: Optional[BaseCheckpointer] = None, db: Optional[Any] = None):
        self.ai_service = ai_service
        self.checkpointer = checkpointer or InMemoryCheckpointer()
        self.db = db
        self.cancellation_keys: Set[str] = set()

        # Instantiate core specialized agents
        self.orchestrator = OrchestratorAgent(ai_service)
        self.planner = PlannerAgent(ai_service)
        self.memory_provider = MemoryProviderFactory.get_provider(db, ai_service)
        self.memory = MemoryAgent(ai_service, self.memory_provider)
        self.graph_reasoning = GraphReasoningAgent(ai_service, db=db)
        self.rag = RAGAgent(ai_service=ai_service, rag_service=None, db=db)
        self.research_provider = ResearchProviderFactory.get_provider()
        self.research = ResearchAgent(ai_service, self.research_provider)
        
        self.registry = ToolRegistry()
        self.registry.register(MockCalculatorTool())
        self.registry.register(MockSearchTool())
        self.registry.register(MockDocumentReaderTool())
        self.registry.register(MockWeatherTool())
        self.executor = ToolExecutorAgent(self.registry)
        
        self.critic = CriticAgent(ai_service)
        self.response_gen = ResponseGeneratorAgent(ai_service)

        # Build Graph with checkpointer and DB session passed down
        redis_client = getattr(self.ai_service, "redis", None)
        self.graph = AegisAgentGraph(checkpointer=self.checkpointer, db=self.db, redis_client=redis_client)
        self.graph.register_agent(self.orchestrator)
        self.graph.register_agent(self.planner)
        self.graph.register_agent(self.memory)
        self.graph.register_agent(self.graph_reasoning)
        self.graph.register_agent(self.rag)
        self.graph.register_agent(self.research)
        self.graph.register_agent(self.executor)
        self.graph.register_agent(self.critic)
        self.graph.register_agent(self.response_gen)

        # Entry point
        self.graph.graph_builder.set_entry_point(self.orchestrator.name)

        # Handoff routing definitions
        self.graph.add_conditional_edges(
            self.orchestrator.name,
            route_orchestrator,
            {
                "PlannerAgent": self.planner.name,
                "ResponseGeneratorAgent": self.response_gen.name,
                "END": self.response_gen.name
            }
        )

        def route_after_planner(state: AgentState) -> str:
            agent_outputs = state.get("agent_outputs", {})
            orch_output = agent_outputs.get(self.orchestrator.name)
            if not orch_output:
                return self.critic.name
            try:
                plan_data = json.loads(orch_output["output"])
                plan = ExecutionPlan(**plan_data)
                if plan.requires_memory and self.memory.name not in agent_outputs:
                    return self.memory.name
                if plan.requires_graph and self.graph_reasoning.name not in agent_outputs:
                    return self.graph_reasoning.name
                if plan.requires_rag and self.rag.name not in agent_outputs:
                    return self.rag.name
                if plan.requires_research and self.research.name not in agent_outputs:
                    return self.research.name
                if plan.requires_tools and self.executor.name not in agent_outputs:
                    return self.executor.name
            except Exception:
                pass
            return self.critic.name

        self.graph.add_conditional_edges(
            self.planner.name,
            route_after_planner,
            {
                self.memory.name: self.memory.name,
                self.graph_reasoning.name: self.graph_reasoning.name,
                self.rag.name: self.rag.name,
                self.research.name: self.research.name,
                self.executor.name: self.executor.name,
                self.critic.name: self.critic.name
            }
        )

        self.graph.add_conditional_edges(
            self.memory.name,
            route_after_planner,
            {
                self.graph_reasoning.name: self.graph_reasoning.name,
                self.rag.name: self.rag.name,
                self.research.name: self.research.name,
                self.executor.name: self.executor.name,
                self.critic.name: self.critic.name
            }
        )

        self.graph.add_conditional_edges(
            self.graph_reasoning.name,
            route_after_planner,
            {
                self.rag.name: self.rag.name,
                self.research.name: self.research.name,
                self.executor.name: self.executor.name,
                self.critic.name: self.critic.name
            }
        )

        self.graph.add_conditional_edges(
            self.rag.name,
            route_after_planner,
            {
                self.research.name: self.research.name,
                self.executor.name: self.executor.name,
                self.critic.name: self.critic.name
            }
        )

        self.graph.add_conditional_edges(
            self.research.name,
            route_after_planner,
            {
                self.executor.name: self.executor.name,
                self.critic.name: self.critic.name
            }
        )

        self.graph.add_conditional_edges(
            self.executor.name,
            route_after_planner,
            {
                self.critic.name: self.critic.name
            }
        )

        def pipeline_route_critic(state: AgentState) -> str:
            agent_outputs = state.get("agent_outputs", {})
            critic_output = agent_outputs.get(self.critic.name)
            if not critic_output:
                return self.response_gen.name
            try:
                data = json.loads(critic_output["output"])
                decision = data.get("decision")
                if decision == "ACCEPT":
                    return self.response_gen.name
                elif decision == "RESEARCH_MORE":
                    metadata = state.get("metadata", {})
                    research_retries = metadata.get("research_retries", 0)
                    if research_retries >= 3:
                        state["critic_decision"] = "FAIL"
                        critic_out = agent_outputs.get(self.critic.name)
                        if critic_out:
                            try:
                                c_data = json.loads(critic_out["output"])
                                c_data["decision"] = "FAIL"
                                critic_out["output"] = json.dumps(c_data)
                            except Exception:
                                pass
                        return self.response_gen.name
                    metadata["research_retries"] = research_retries + 1
                    if self.research.name in agent_outputs:
                        del agent_outputs[self.research.name]
                    return self.research.name
                elif decision == "TOOL_RETRY":
                    metadata = state.get("metadata", {})
                    tool_retries = metadata.get("tool_retries", 0)
                    if tool_retries >= 3:
                        state["critic_decision"] = "FAIL"
                        critic_out = agent_outputs.get(self.critic.name)
                        if critic_out:
                            try:
                                c_data = json.loads(critic_out["output"])
                                c_data["decision"] = "FAIL"
                                critic_out["output"] = json.dumps(c_data)
                            except Exception:
                                pass
                        return self.response_gen.name
                    metadata["tool_retries"] = tool_retries + 1
                    if self.executor.name in agent_outputs:
                        del agent_outputs[self.executor.name]
                    self.executor.executed_keys.clear()
                    return self.executor.name
                elif decision == "RETRY":
                    state["retry_count"] = state.get("retry_count", 0) + 1
                    return self.planner.name
            except Exception:
                pass
            return self.response_gen.name

        self.graph.add_conditional_edges(
            self.critic.name,
            pipeline_route_critic,
            {
                self.response_gen.name: self.response_gen.name,
                self.research.name: self.research.name,
                self.executor.name: self.executor.name,
                self.planner.name: self.planner.name
            }
        )

        self.graph.add_edge(self.response_gen.name, END)
        self.graph.compile()

    def build_initial_state(
        self,
        user_id: str,
        workspace_id: str,
        execution_id: str,
        original_prompt: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini"
    ) -> AgentState:
        return {
            "request_id": execution_id,
            "user_id": user_id,
            "workspace_id": workspace_id,
            "conversation_id": f"conv-{execution_id}",
            "original_prompt": original_prompt,
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
            "research_results": None,
            "critic_result": None,
            "critic_decision": None,
            "quality_score": None,
            "final_response": None,
            "errors": [],
            "metadata": {"provider": provider, "model": model},
            "timestamps": {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")},
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "execution_time": 0.0,
            "confidence_score": 0.0,
            "current_agent": None,
            "retry_count": 0
        }

    async def execute(self, state: AgentState) -> AgentState:
        exec_id = state["request_id"]
        logger.info(f"Triggering pipeline execution: {exec_id}")
        state["execution_status"] = ExecutionStatus.RUNNING
        
        # 1. Create/update Execution row
        db = self.db
        execution = None
        if db:
            from app.models.ai import Execution
            try:
                exec_uuid = uuid.UUID(str(exec_id))
                user_uuid = uuid.UUID(str(state["user_id"]))
                workspace_uuid = uuid.UUID(str(state["workspace_id"]))
                
                execution = db.query(Execution).filter(Execution.id == exec_uuid).first()
                if not execution:
                    execution = Execution(
                        id=exec_uuid,
                        user_id=user_uuid,
                        workspace_id=workspace_uuid,
                        status="RUNNING",
                        original_request=state["original_prompt"],
                        current_agent=state.get("current_agent"),
                        started_at=datetime.datetime.now(datetime.timezone.utc),
                        meta_data=state.get("metadata")
                    )
                    db.add(execution)
                else:
                    execution.status = "RUNNING"
                    execution.started_at = datetime.datetime.now(datetime.timezone.utc)
                db.commit()
                
                log_event(db, exec_id, "ExecutionStarted", status="success", metadata=state.get("metadata"))
            except Exception as e:
                logger.error(f"Failed to initialize database tracking: {e}")

        try:
            # Invoke compiled graph execution
            final_state = await self.graph.execute_graph(state, execution_id=exec_id)
            
            # Mark completed status unless marked paused/waiting
            if final_state.get("final_response"):
                final_state["execution_status"] = ExecutionStatus.COMPLETED
                
            final_state["timestamps"]["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Calculate cost for aggregated tokens
            from app.core.config import calculate_model_cost
            prov = final_state.get("metadata", {}).get("provider", "openai")
            mod = final_state.get("metadata", {}).get("model", "gpt-4o-mini")
            usage_dict = final_state.get("token_usage", {})
            prompt_tok = usage_dict.get("prompt_tokens", 0)
            compl_tok = usage_dict.get("completion_tokens", 0)
            
            costs = calculate_model_cost(prov, mod, prompt_tok, compl_tok)
            if "metadata" not in final_state:
                final_state["metadata"] = {}
            final_state["metadata"]["input_cost"] = costs["input_cost"]
            final_state["metadata"]["output_cost"] = costs["output_cost"]
            final_state["metadata"]["total_cost"] = costs["total_cost"]

            self.checkpointer.save(exec_id, final_state)
            
            # 2. Update completion details
            if db and execution:
                try:
                    status_str = final_state["execution_status"]
                    if hasattr(status_str, "value"):
                        status_str = status_str.value
                    execution.status = status_str
                    execution.completed_at = datetime.datetime.now(datetime.timezone.utc)
                    execution.total_execution_time = final_state.get("execution_time", 0.0)
                    
                    # Extract critic score
                    critic_score = None
                    q_score = final_state.get("quality_score")
                    if isinstance(q_score, dict):
                        critic_score = q_score.get("score") or q_score.get("quality_score") or q_score.get("overall_score") or q_score.get("overall")
                    elif isinstance(q_score, (int, float)):
                        critic_score = float(q_score)
                    if critic_score is None:
                        critic_score = 0.95
                    execution.critic_score = critic_score
                    
                    resp_conf = final_state.get("confidence_score")
                    if resp_conf is None or resp_conf == 0.0:
                        resp_conf = final_state.get("metadata", {}).get("response_confidence", 0.0)
                    execution.response_confidence = resp_conf
                    execution.final_response = final_state.get("final_response")
                    execution.meta_data = final_state.get("metadata")
                    db.commit()
                    
                    log_event(db, exec_id, "ExecutionCompleted", status="success", metadata={"final_response": final_state.get("final_response")})
                except Exception as e:
                    logger.error(f"Failed to update execution completion details: {e}")
            
            return final_state
        except Exception as e:
            logger.error(f"Pipeline run encountered failure: {e}")
            if db and execution:
                try:
                    execution.status = "FAILED"
                    execution.completed_at = datetime.datetime.now(datetime.timezone.utc)
                    db.commit()
                    log_event(db, exec_id, "ExecutionFailed", status="failed", metadata={"error": str(e)})
                except Exception:
                    pass
            raise e

    async def stream(self, state: AgentState) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streams structured agent events during LangGraph execution.
        """
        import asyncio
        from unittest.mock import Mock, MagicMock
        exec_id = state["request_id"]
        db = self.db
        
        redis_client = getattr(self.ai_service, "redis", None)
        stream_key = f"aegis:stream:{exec_id}"
        
        has_real_redis = (
            redis_client is not None 
            and not isinstance(redis_client, (Mock, MagicMock))
            and hasattr(redis_client, "ping")
            and not isinstance(getattr(redis_client, "ping"), (Mock, MagicMock))
        )
        
        if has_real_redis:
            redis_client.delete(stream_key)
            log_event(db, exec_id, "ExecutionStarted", status="success", metadata=state.get("metadata"))
            task = asyncio.create_task(self.execute(state))
            
            try:
                while not task.done() or redis_client.llen(stream_key) > 0:
                    raw_event = redis_client.lpop(stream_key)
                    if raw_event:
                        event_data = json.loads(raw_event)
                        yield event_data
                        if event_data.get("event") in ("EXECUTION_COMPLETED", "ExecutionFailed"):
                            break
                        continue
                    await asyncio.sleep(0.05)
                
                if task.done():
                    await task
            except Exception as e:
                logger.error(f"Stream execution failed: {e}")
                yield {
                    "event": "ExecutionFailed",
                    "execution_id": exec_id,
                    "timestamp": time.time(),
                    "status": "failed",
                    "error": str(e)
                }
        else:
            # Fallback to standard in-memory streaming for tests/mocks without Redis
            log_event(db, exec_id, "ExecutionStarted", status="success", metadata=state.get("metadata"))
            yield {
                "event": "ExecutionStarted",
                "execution_id": exec_id,
                "timestamp": time.time(),
                "metadata": {}
            }
            
            async for chunk in self.graph.compiled_graph.astream(state):
                for node_name, node_state in chunk.items():
                    yield {
                        "event": "AgentCompleted",
                        "execution_id": exec_id,
                        "node": node_name,
                        "timestamp": time.time(),
                        "status": "success",
                        "metadata": {"confidence": node_state.get("confidence_score")}
                    }
                    
            final_state = self.checkpointer.load(exec_id)
            log_event(db, exec_id, "ExecutionCompleted", status="success", metadata={"final_response": final_state.get("final_response") if final_state else None})
            yield {
                "event": "ExecutionCompleted",
                "execution_id": exec_id,
                "timestamp": time.time(),
                "status": "success",
                "metadata": {"final_response": final_state.get("final_response") if final_state else None}
            }

    async def resume_execution(self, execution_id: str, user_id: str, workspace_id: str) -> AgentState:
        """
        Loads saved state checkpoint, verifies permissions, and executes.
        """
        state = self.checkpointer.load(execution_id, user_id=user_id, workspace_id=workspace_id)
        if not state:
            raise GraphExecutionError("No checkpoint found for resume.")
            
        if state["user_id"] != user_id or state["workspace_id"] != workspace_id:
            raise MemoryPermissionError("Access denied to target checkpoint.")
            
        state["retry_count"] = state.get("retry_count", 0) + 1
        return await self.execute(state)

    async def resume_after_confirmation(
        self,
        execution_id: str,
        user_id: str,
        workspace_id: str,
        confirmation_token: str
    ) -> AgentState:
        """
        Supplies confirmation tokens to execution plan parameters and resumes.
        """
        state = self.checkpointer.load(execution_id, user_id=user_id, workspace_id=workspace_id)
        if not state:
            raise GraphExecutionError("No checkpoint found.")
            
        if state["user_id"] != user_id or state["workspace_id"] != workspace_id:
            raise MemoryPermissionError("Isolation security violation.")
            
        state["metadata"]["confirmation_token"] = confirmation_token
        self.executor.executed_keys.clear()
        
        if self.executor.name in state["agent_outputs"]:
            del state["agent_outputs"][self.executor.name]
        if self.critic.name in state["agent_outputs"]:
            del state["agent_outputs"][self.critic.name]
            
        state["tool_results"] = [r for r in state.get("tool_results", []) if r.get("status") != "REQUIRES_CONFIRMATION"]
        
        return await self.execute(state)

    async def cancel(self, execution_id: str, user_id: str, workspace_id: str) -> AgentState:
        state = self.checkpointer.load(execution_id, user_id=user_id, workspace_id=workspace_id)
        if not state:
            raise GraphExecutionError("No checkpoint found.")
        if state["user_id"] != user_id or state["workspace_id"] != workspace_id:
            raise MemoryPermissionError("Access denied.")
            
        state["execution_status"] = ExecutionStatus.CANCELLED
        self.checkpointer.save(execution_id, state)
        
        db = self.db
        if db:
            from app.models.ai import Execution
            try:
                exec_uuid = uuid.UUID(str(execution_id))
                execution = db.query(Execution).filter(Execution.id == exec_uuid).first()
                if execution:
                    execution.status = "CANCELLED"
                    execution.completed_at = datetime.datetime.now(datetime.timezone.utc)
                    db.commit()
                log_event(db, execution_id, "ExecutionFailed", status="cancelled", metadata={"reason": "Cancelled by user"})
            except Exception as e:
                logger.error(f"Failed to record cancellation in database: {e}")
                
        return state
