import pytest
from typing import Dict, Any
from app.core.agent.state import AgentState, ExecutionStatus
from app.core.agent.base import BaseAgent, AgentResult, ExecutionContext
from app.core.agent.checkpoint import InMemoryCheckpointer
from app.core.agent.graph import AegisAgentGraph, END
from app.core.agent.exceptions import GraphExecutionError

class DummyAgent(BaseAgent):
    """
    Test agent node.
    """
    @property
    def name(self) -> str:
        return "DummyAgent"

    @property
    def description(self) -> str:
        return "A dummy agent for testing node integrations."

    def validate_input(self, state: AgentState) -> bool:
        # Require original prompt to run
        return bool(state.get("original_prompt"))

    def validate_output(self, result: AgentResult) -> bool:
        return result.confidence > 0.5

    def health_check(self) -> bool:
        return True

    async def execute(self, state: AgentState, context: ExecutionContext) -> AgentResult:
        return AgentResult(
            agent_name=self.name,
            status="success",
            output="Executed Dummy Node output",
            confidence=0.95,
            execution_time=0.02,
            token_usage={"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25}
        )

def test_agent_result_validation():
    # Verify Pydantic validation handles standard input correctly
    res = AgentResult(
        agent_name="TestAgent",
        status="completed",
        output="Result payload text",
        confidence=0.8,
        execution_time=0.15,
        token_usage={"total_tokens": 120}
    )
    assert res.agent_name == "TestAgent"
    assert res.confidence == 0.8

@pytest.mark.asyncio
async def test_graph_compilation_and_run():
    checkpointer = InMemoryCheckpointer()
    graph = AegisAgentGraph(checkpointer=checkpointer)
    
    agent = DummyAgent()
    graph.register_agent(agent)
    
    # Simple direct single-node graph structure
    graph.add_edge(agent.name, END)
    graph.graph_builder.set_entry_point(agent.name)
    
    # Compile
    graph.compile()
    
    initial_state: AgentState = {
        "request_id": "req-123",
        "user_id": "user-456",
        "workspace_id": "ws-789",
        "conversation_id": "conv-000",
        "original_prompt": "Hello graph engine",
        "current_task": "DummyAgent",
        "execution_status": ExecutionStatus.PENDING,
        "execution_plan": [],
        "messages": [],
        "agent_outputs": {},
        "tool_results": [],
        "memory_context": None,
        "research_results": None,
        "critic_result": None,
        "final_response": None,
        "errors": [],
        "metadata": {},
        "timestamps": {},
        "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "execution_time": 0.0,
        "confidence_score": 0.0,
        "current_agent": None,
        "retry_count": 0
    }
    
    exec_id = "test-exec-uuid"
    final_state = await graph.execute_graph(initial_state, execution_id=exec_id)
    
    assert final_state["current_agent"] == "DummyAgent"
    assert final_state["token_usage"]["total_tokens"] == 25
    assert final_state["final_response"] == "Executed Dummy Node output"
    
    # Checkpoint verification
    saved_state = checkpointer.load(exec_id)
    assert saved_state is not None
    assert saved_state["current_agent"] == "DummyAgent"

@pytest.mark.asyncio
async def test_graph_validation_error():
    graph = AegisAgentGraph()
    agent = DummyAgent()
    graph.register_agent(agent)
    graph.add_edge(agent.name, END)
    graph.graph_builder.set_entry_point(agent.name)
    graph.compile()
    
    # Set missing original_prompt to trigger validate_input failure
    initial_state: AgentState = {
        "request_id": "req-123",
        "user_id": "user-456",
        "workspace_id": "ws-789",
        "conversation_id": "conv-000",
        "original_prompt": "",  # Empty prompt fails validation check
        "current_task": "DummyAgent",
        "execution_status": ExecutionStatus.PENDING,
        "execution_plan": [],
        "messages": [],
        "agent_outputs": {},
        "tool_results": [],
        "memory_context": None,
        "research_results": None,
        "critic_result": None,
        "final_response": None,
        "errors": [],
        "metadata": {},
        "timestamps": {},
        "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "execution_time": 0.0,
        "confidence_score": 0.0,
        "current_agent": None,
        "retry_count": 0
    }
    
    with pytest.raises(GraphExecutionError):
        await graph.execute_graph(initial_state)
