import uuid
import time
import json
import datetime
from typing import Dict, Any, List, Optional
from loguru import logger
from langgraph.graph import StateGraph, END

from app.core.agent.state import AgentState, ExecutionStatus
from app.core.agent.base import BaseAgent, ExecutionContext, AgentResult
from app.core.agent.checkpoint import BaseCheckpointer
from app.core.agent.exceptions import GraphExecutionError

def log_event(db: Any, execution_id: str, event_type: str, agent_type: Optional[str] = None, status: str = "success", metadata: Optional[dict] = None) -> None:
    from app.models.ai import ExecutionEvent
    import redis
    from app.database.redis import redis_pool
    if not db:
        return
    try:
        event = ExecutionEvent(
            execution_id=uuid.UUID(str(execution_id)) if isinstance(execution_id, (str, uuid.UUID)) else execution_id,
            event_type=event_type,
            agent_type=agent_type,
            status=status,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            meta_data=metadata
        )
        db.add(event)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log event {event_type} in database: {e}")

    try:
        mapped_event_type = event_type
        if event_type == "AgentStarted":
            if agent_type == "OrchestratorAgent":
                mapped_event_type = "ORCHESTRATOR_STARTED"
            elif agent_type == "PlannerAgent":
                mapped_event_type = "PLANNER_STARTED"
            elif agent_type == "ResearchAgent":
                mapped_event_type = "RESEARCH_STARTED"
            elif agent_type == "MemoryAgent":
                mapped_event_type = "MEMORY_STARTED"
            elif agent_type == "ToolExecutorAgent":
                mapped_event_type = "TOOL_STARTED"
            elif agent_type == "CriticAgent":
                mapped_event_type = "CRITIC_STARTED"
            elif agent_type == "ResponseGeneratorAgent":
                mapped_event_type = "RESPONSE_GENERATING"
        elif event_type == "ToolStarted":
            mapped_event_type = "TOOL_STARTED"
        elif event_type == "ToolCompleted":
            mapped_event_type = "TOOL_COMPLETED"
        elif event_type == "ExecutionStarted":
            mapped_event_type = "EXECUTION_STARTED"
        elif event_type == "ExecutionCompleted":
            mapped_event_type = "EXECUTION_COMPLETED"
            
        client = redis.Redis(connection_pool=redis_pool)
        stream_key = f"aegis:stream:{execution_id}"
        
        safe_meta = {}
        if metadata:
            for k, v in metadata.items():
                if k in ("error", "reason", "confidence", "tool_id", "status"):
                    safe_meta[k] = v
                    
        client.rpush(stream_key, json.dumps({
            "event": mapped_event_type,
            "execution_id": str(execution_id),
            "timestamp": time.time(),
            "status": status,
            "metadata": safe_meta
        }))
        client.close()
    except Exception as re:
        logger.error(f"Failed to publish event {event_type} to Redis: {re}")


class AegisAgentGraph:
    """
    LangGraph infrastructure for orchestrating node mappings and state transitions.
    """
    def __init__(self, checkpointer: Optional[BaseCheckpointer] = None, db: Optional[Any] = None, redis_client: Optional[Any] = None):
        self.graph_builder = StateGraph(AgentState)
        self.agents: Dict[str, BaseAgent] = {}
        self.checkpointer = checkpointer
        self.db = db
        self.redis_client = redis_client
        self.compiled_graph = None

    def register_agent(self, agent: BaseAgent):
        """
        Registers an autonomous agent and mounts it as a node.
        """
        self.agents[agent.name] = agent
        
        async def node_wrapper(state: AgentState) -> Dict[str, Any]:
            logger.info(f"Entering node execution for: {agent.name}")
            db = self.db
            exec_id = state.get("request_id", "")
            
            # Check for cancellation before executing node
            if self.redis_client:
                cancel_key = f"aegis:cancel:{exec_id}"
                if self.redis_client.get(cancel_key):
                    logger.info(f"Cancellation signal detected for execution: {exec_id}")
                    raise GraphExecutionError("Execution cancelled by user.")
            
            # Prepare execution context with database session
            config = {}
            if db:
                config["db"] = db
            context = ExecutionContext(
                request_id=exec_id,
                user_id=state.get("user_id", ""),
                workspace_id=state.get("workspace_id", ""),
                conversation_id=state.get("conversation_id", ""),
                model=state.get("metadata", {}).get("model", "gpt-4o-mini"),
                provider=state.get("metadata", {}).get("provider", "openai"),
                configuration=config
            )
            
            # Log AgentStarted event and create AgentExecution row
            agent_exec = None
            if db:
                from app.models.ai import AgentExecution
                try:
                    agent_exec = AgentExecution(
                        execution_id=uuid.UUID(str(exec_id)),
                        agent_type=agent.name,
                        status="RUNNING",
                        started_at=datetime.datetime.now(datetime.timezone.utc),
                        retry_count=state.get("retry_count", 0),
                        meta_data=state.get("metadata")
                    )
                    db.add(agent_exec)
                    db.commit()
                    
                    # Log AgentStarted event
                    log_event(db, exec_id, "AgentStarted", agent_type=agent.name, status="success")
                    
                    # Log specific start events
                    if agent.name == "ResearchAgent":
                        log_event(db, exec_id, "ResearchStarted", agent_type=agent.name, status="success")
                except Exception as e:
                    logger.error(f"Database tracking setup failed for {agent.name}: {e}")
            
            # Validate input
            if not agent.validate_input(state):
                err_msg = f"Input validation failed for agent: {agent.name}"
                if db and agent_exec:
                    try:
                        agent_exec.status = "FAILED"
                        agent_exec.error = err_msg
                        db.commit()
                        log_event(db, exec_id, "AgentFailed", agent_type=agent.name, status="failed", metadata={"error": err_msg})
                    except Exception:
                        pass
                raise GraphExecutionError(err_msg)
                
            start_time = time.perf_counter()
            try:
                result = await agent.execute(state, context)
                latency = time.perf_counter() - start_time
                
                # Validate output
                if not agent.validate_output(result):
                    raise GraphExecutionError(f"Output validation failed for agent: {agent.name}")
                    
                # Update AgentExecution and log completed event
                if db and agent_exec:
                    try:
                        agent_exec.status = "COMPLETED"
                        agent_exec.completed_at = datetime.datetime.now(datetime.timezone.utc)
                        agent_exec.duration = latency
                        agent_exec.quality_score = result.confidence
                        agent_exec.meta_data = result.metadata
                        db.commit()
                        
                        log_event(db, exec_id, "AgentCompleted", agent_type=agent.name, status="success", metadata={"duration": latency})
                        
                        # Log specific completed events
                        if agent.name == "ResearchAgent":
                            log_event(db, exec_id, "ResearchCompleted", agent_type=agent.name, status="success")
                        elif agent.name == "MemoryAgent":
                            log_event(db, exec_id, "MemoryRetrieved", agent_type=agent.name, status="success")
                        elif agent.name == "CriticAgent":
                            log_event(db, exec_id, "CriticEvaluated", agent_type=agent.name, status="success", metadata={"decision": state.get("critic_decision")})
                        elif agent.name == "ResponseGeneratorAgent":
                            log_event(db, exec_id, "ResponseGenerated", agent_type=agent.name, status="success")
                    except Exception as e:
                        logger.error(f"Failed to save agent run details to database: {e}")
            except Exception as e:
                logger.error(f"Node execution failed for {agent.name}: {e}")
                latency = time.perf_counter() - start_time
                if agent.name == "ToolExecutorAgent":
                    tool_res_list = state.get("tool_results", [])
                    tool_res_list.append({
                        "execution_id": exec_id,
                        "tool_id": "calculator",
                        "status": "FAILED",
                        "error": str(e),
                        "execution_time": latency
                    })
                
                # Update AgentExecution failure and log failed event
                if db and agent_exec:
                    try:
                        agent_exec.status = "FAILED"
                        agent_exec.completed_at = datetime.datetime.now(datetime.timezone.utc)
                        agent_exec.duration = latency
                        agent_exec.error = str(e)
                        db.commit()
                        
                        log_event(db, exec_id, "AgentFailed", agent_type=agent.name, status="failed", metadata={"error": str(e)})
                        if agent.name == "ResearchAgent":
                            log_event(db, exec_id, "ResearchCompleted", agent_type=agent.name, status="failed", metadata={"error": str(e)})
                    except Exception as db_err:
                        logger.error(f"Failed to log agent failure in database: {db_err}")
                        
                result = AgentResult(
                    agent_name=agent.name,
                    status="failed",
                    output=json.dumps({"status": "FAILED", "error": str(e)}),
                    confidence=0.0,
                    execution_time=latency,
                    token_usage={}
                )

            # Log output to state map
            agent_outputs = state.get("agent_outputs", {})
            agent_outputs[agent.name] = result.model_dump()
            
            # Aggregate token usage
            state_tokens = state.get("token_usage", {})
            aggregated_tokens = {
                "prompt_tokens": state_tokens.get("prompt_tokens", 0) + result.token_usage.get("prompt_tokens", 0),
                "completion_tokens": state_tokens.get("completion_tokens", 0) + result.token_usage.get("completion_tokens", 0),
                "total_tokens": state_tokens.get("total_tokens", 0) + result.token_usage.get("total_tokens", 0)
            }
            
            research_res = state.get("research_results")
            if agent.name == "ResearchAgent":
                research_res = result.output
                
            memory_ctx = state.get("memory_context")
            if agent.name == "MemoryAgent":
                memory_ctx = result.output
                
            critic_res = state.get("critic_result")
            critic_dec = state.get("critic_decision")
            quality_sc = state.get("quality_score")
            if agent.name == "CriticAgent" and result.output:
                critic_res = result.output
                try:
                    cdata = json.loads(result.output)
                    critic_dec = cdata.get("decision")
                    quality_sc = cdata
                except Exception:
                    pass

            final_resp = state.get("final_response")
            conf_score = state.get("confidence_score", 0.0)
            if agent.name == "ResponseGeneratorAgent" and result.output:
                try:
                    rdata = json.loads(result.output)
                    final_resp = rdata.get("content")
                    conf_score = rdata.get("confidence") or result.confidence
                except Exception:
                    final_resp = result.output
                    conf_score = result.confidence
            elif agent.name == state.get("current_task"):
                final_resp = result.output

            return {
                "agent_outputs": agent_outputs,
                "current_agent": agent.name,
                "execution_time": state.get("execution_time", 0.0) + latency,
                "token_usage": aggregated_tokens,
                "research_results": research_res,
                "memory_context": memory_ctx,
                "critic_result": critic_res,
                "critic_decision": critic_dec,
                "quality_score": quality_sc,
                "confidence_score": conf_score,
                "final_response": final_resp
            }
            
        self.graph_builder.add_node(agent.name, node_wrapper)

    def add_edge(self, start_node: str, end_node: str):
        self.graph_builder.add_edge(start_node, end_node)

    def add_conditional_edges(
        self,
        source: str,
        path: Any,
        path_map: Dict[str, str]
    ):
        self.graph_builder.add_conditional_edges(source, path, path_map)

    def compile(self):
        self.compiled_graph = self.graph_builder.compile()
        return self.compiled_graph

    async def execute_graph(self, initial_state: AgentState, execution_id: Optional[str] = None) -> AgentState:
        """
        Triggers graph execution cycle.
        """
        if not self.compiled_graph:
            self.compile()
            
        exec_id = execution_id or str(uuid.uuid4())
        logger.info(f"Starting agent graph execution cycle. Execution ID: {exec_id}")
        
        try:
            # Execute through LangGraph compiled app
            final_state = await self.compiled_graph.ainvoke(initial_state)
            
            # Save checkpoint
            if self.checkpointer:
                self.checkpointer.save(exec_id, final_state)
                
            return final_state
        except Exception as e:
            logger.error(f"Graph execution failed. Error: {e}")
            raise GraphExecutionError(f"Execution failed on graph: {e}")
