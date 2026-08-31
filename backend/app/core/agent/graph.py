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
import redis
from app.database.redis import redis_pool

_redis_available_status: Optional[bool] = None

def is_redis_available() -> bool:
    global _redis_available_status
    if _redis_available_status is False:
        return False
    if _redis_available_status is True:
        return True
    try:
        c = redis.Redis(connection_pool=redis_pool, socket_connect_timeout=0.05, socket_timeout=0.05)
        c.ping()
        _redis_available_status = True
        return True
    except Exception:
        _redis_available_status = False
        return False

def log_event(
    db: Optional[Any],
    execution_id: str,
    event_type: str,
    agent_type: Optional[str] = None,
    tool_id: Optional[str] = None,
    status: str = "success",
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Publishes execution events to Redis Streams and saves persistent audit trails to DB.
    """
    event_meta = dict(metadata or {})
    if tool_id:
        event_meta["tool_id"] = tool_id

    if db:
        try:
            from app.models.ai import ExecutionEvent
            event = ExecutionEvent(
                execution_id=uuid.UUID(str(execution_id)),
                event_type=event_type,
                agent_type=agent_type,
                status=status,
                meta_data=event_meta
            )
            db.add(event)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log execution event to DB: {e}")
            
    # Publish structured real-time event to Redis Streams
    if not is_redis_available():
        return

    try:
        mapped_event_type = event_type
        if event_type == "AgentStarted":
            if agent_type == "OrchestratorAgent":
                mapped_event_type = "ORCHESTRATOR_STARTED"
            elif agent_type == "PlannerAgent":
                mapped_event_type = "PLANNER_STARTED"
            elif agent_type == "GraphReasoningAgent":
                mapped_event_type = "GRAPH_REASONING_STARTED"
            elif agent_type == "RAGAgent":
                mapped_event_type = "RAG_STARTED"
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
        elif event_type == "AgentCompleted":
            if agent_type == "GraphReasoningAgent":
                mapped_event_type = "GRAPH_REASONING_COMPLETED"
            elif agent_type == "RAGAgent":
                mapped_event_type = "RAG_COMPLETED"
            else:
                mapped_event_type = f"AGENT_COMPLETED_{agent_type.upper() if agent_type else 'UNKNOWN'}"
        elif event_type == "AgentFailed":
            if agent_type == "GraphReasoningAgent":
                mapped_event_type = "GRAPH_REASONING_FAILED"
            elif agent_type == "RAGAgent":
                mapped_event_type = "RAG_FAILED"
            else:
                mapped_event_type = "AGENT_FAILED"
        elif event_type == "ExecutionStarted":
            mapped_event_type = "EXECUTION_STARTED"
        elif event_type == "ExecutionCompleted":
            mapped_event_type = "EXECUTION_COMPLETED"
        elif event_type == "ToolStarted":
            mapped_event_type = "TOOL_STARTED"
        elif event_type == "ToolCompleted":
            mapped_event_type = "TOOL_COMPLETED"
        elif event_type.startswith("MCP_"):
            mapped_event_type = event_type
            
        client = redis.Redis(connection_pool=redis_pool, socket_connect_timeout=0.02, socket_timeout=0.02)
        stream_key = f"aegis:stream:{execution_id}"
        
        safe_meta = {}
        if metadata:
            for k, v in metadata.items():
                if k in ("error", "reason", "confidence", "tool_id", "status", "citations_count", "chunks_count", "tool_name", "resource_id", "prompt_id", "server_id", "source", "trust_label"):
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
        logger.debug(f"Event streaming to Redis skipped or unavailable: {re}")


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
                    elif agent.name == "RAGAgent":
                        log_event(db, exec_id, "RAGStarted", agent_type=agent.name, status="success")
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
                        elif agent.name == "RAGAgent":
                            log_event(db, exec_id, "RAGCompleted", agent_type=agent.name, status="success")
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
                        "tool_id": "system_error",
                        "status": "FAILED",
                        "output": {},
                        "error": str(e),
                        "execution_time": latency
                    })
                    state["tool_results"] = tool_res_list
                if db and agent_exec:
                    try:
                        agent_exec.status = "FAILED"
                        agent_exec.completed_at = datetime.datetime.now(datetime.timezone.utc)
                        agent_exec.duration = latency
                        agent_exec.error = str(e)
                        db.commit()
                        log_event(db, exec_id, "AgentFailed", agent_type=agent.name, status="failed", metadata={"error": str(e)})
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

            # Update shared state dict
            if "agent_outputs" not in state:
                state["agent_outputs"] = {}
            state["agent_outputs"][agent.name] = result.model_dump()
            state["current_agent"] = agent.name

            # Aggregate token usage
            state_tokens = state.get("token_usage", {})
            aggregated_tokens = {
                "prompt_tokens": state_tokens.get("prompt_tokens", 0) + result.token_usage.get("prompt_tokens", 0),
                "completion_tokens": state_tokens.get("completion_tokens", 0) + result.token_usage.get("completion_tokens", 0),
                "total_tokens": state_tokens.get("total_tokens", 0) + result.token_usage.get("total_tokens", 0)
            }
            state["token_usage"] = aggregated_tokens
            state["execution_time"] = state.get("execution_time", 0.0) + latency
            
            # Map memory output into memory_context
            if agent.name == "MemoryAgent" and result.status == "success":
                try:
                    mem_data = json.loads(result.output)
                    state["memory_context"] = mem_data.get("context", "")
                    state["memory_results"] = mem_data
                except Exception as me:
                    logger.error(f"Failed to extract memory context from output: {me}")

            # Map research output into research_results
            if agent.name == "ResearchAgent" and result.status == "success":
                state["research_results"] = result.output

            # Map critic outputs
            if agent.name == "CriticAgent":
                try:
                    crit_data = json.loads(result.output)
                    state["critic_result"] = result.output
                    state["critic_decision"] = crit_data.get("decision")
                    state["quality_score"] = {"overall": crit_data.get("overall_score", 1.0), "overall_score": crit_data.get("overall_score", 1.0)}
                except Exception as ce:
                    logger.error(f"Failed to parse critic result: {ce}")

            # Map ToolExecutorAgent outputs for MCP resources and prompts
            if agent.name == "ToolExecutorAgent" and result.status == "success":
                try:
                    tr_data = json.loads(result.output)
                    if tr_data.get("metadata", {}).get("source") == "MCP_RESOURCE":
                        state["mcp_resource_context"] = tr_data.get("output", {}).get("content", "")
                    elif tr_data.get("metadata", {}).get("source") == "MCP_PROMPT":
                        state["mcp_prompt_context"] = json.dumps(tr_data.get("output", {}).get("messages", []))
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
                conf_score = result.confidence

            state["final_response"] = final_resp
            state["confidence_score"] = conf_score

            # Persist checkpoint to database
            if self.checkpointer:
                try:
                    self.checkpointer.save(exec_id, state)
                except Exception as cpe:
                    logger.error(f"Failed to persist state checkpoint: {cpe}")
            
            return {
                "agent_outputs": state["agent_outputs"],
                "current_agent": state["current_agent"],
                "memory_context": state.get("memory_context"),
                "memory_results": state.get("memory_results"),
                "rag_result": state.get("rag_result"),
                "rag_context": state.get("rag_context"),
                "rag_citations": state.get("rag_citations"),
                "rag_confidence": state.get("rag_confidence"),
                "graph_context": state.get("graph_context"),
                "research_results": state.get("research_results"),
                "mcp_resource_context": state.get("mcp_resource_context"),
                "mcp_prompt_context": state.get("mcp_prompt_context"),
                "mcp_citations": state.get("mcp_citations"),
                "mcp_pending_confirmation": state.get("mcp_pending_confirmation"),
                "mcp_execution_results": state.get("mcp_execution_results"),
                "critic_result": state.get("critic_result"),
                "critic_decision": state.get("critic_decision"),
                "quality_score": state.get("quality_score"),
                "final_response": final_resp,
                "confidence_score": conf_score,
                "tool_results": state.get("tool_results", []),
                "token_usage": state.get("token_usage", {}),
                "execution_time": state.get("execution_time", 0.0),
                "metadata": state.get("metadata", {}),
                "execution_status": state.get("execution_status", ExecutionStatus.RUNNING),
                "retry_count": state.get("retry_count", 0)
            }

        self.graph_builder.add_node(agent.name, node_wrapper)

    def add_edge(self, from_agent: str, to_agent: str):
        self.graph_builder.add_edge(from_agent, to_agent)

    def add_conditional_edges(self, source: str, path_fn: Any, path_map: Dict[str, str]):
        self.graph_builder.add_conditional_edges(source, path_fn, path_map)

    def compile(self):
        if not self.compiled_graph:
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
            final_state = await self.compiled_graph.ainvoke(initial_state)
            if self.checkpointer:
                self.checkpointer.save(exec_id, final_state)
            return final_state
        except Exception as e:
            logger.error(f"Graph execution failed. Error: {e}")
            raise GraphExecutionError(f"Execution failed on graph: {e}")
