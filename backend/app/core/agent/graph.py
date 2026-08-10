import uuid
import time
from typing import Dict, Any, List, Optional
from loguru import logger
from langgraph.graph import StateGraph, END

from app.core.agent.state import AgentState, ExecutionStatus
from app.core.agent.base import BaseAgent, ExecutionContext
from app.core.agent.checkpoint import BaseCheckpointer
from app.core.agent.exceptions import GraphExecutionError

class AegisAgentGraph:
    """
    LangGraph infrastructure for orchestrating node mappings and state transitions.
    """
    def __init__(self, checkpointer: Optional[BaseCheckpointer] = None):
        self.graph_builder = StateGraph(AgentState)
        self.agents: Dict[str, BaseAgent] = {}
        self.checkpointer = checkpointer
        self.compiled_graph = None

    def register_agent(self, agent: BaseAgent):
        """
        Registers an autonomous agent and mounts it as a node.
        """
        self.agents[agent.name] = agent
        
        async def node_wrapper(state: AgentState) -> Dict[str, Any]:
            logger.info(f"Entering node execution for: {agent.name}")
            
            # Prepare execution context
            context = ExecutionContext(
                request_id=state.get("request_id", ""),
                user_id=state.get("user_id", ""),
                workspace_id=state.get("workspace_id", ""),
                conversation_id=state.get("conversation_id", ""),
                model=state.get("metadata", {}).get("model", "gpt-4o-mini"),
                provider=state.get("metadata", {}).get("provider", "openai")
            )
            
            # Validate input
            if not agent.validate_input(state):
                raise GraphExecutionError(f"Input validation failed for agent: {agent.name}")
                
            start_time = time.perf_counter()
            result = await agent.execute(state, context)
            latency = time.perf_counter() - start_time
            
            # Validate output
            if not agent.validate_output(result):
                raise GraphExecutionError(f"Output validation failed for agent: {agent.name}")
                
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
            
            return {
                "agent_outputs": agent_outputs,
                "current_agent": agent.name,
                "execution_time": state.get("execution_time", 0.0) + latency,
                "token_usage": aggregated_tokens,
                "final_response": result.output if agent.name == state.get("current_task") else state.get("final_response")
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
