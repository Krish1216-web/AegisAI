from enum import Enum
from typing import TypedDict, List, Dict, Any, Optional

class ExecutionStatus(str, Enum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    RESEARCHING = "RESEARCHING"
    MEMORY_RETRIEVAL = "MEMORY_RETRIEVAL"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    CRITIC_REVIEW = "CRITIC_REVIEW"
    GENERATING_RESPONSE = "GENERATING_RESPONSE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"
    RUNNING = "RUNNING"
    WAITING_FOR_CONFIRMATION = "WAITING_FOR_CONFIRMATION"
    WAITING_FOR_CLARIFICATION = "WAITING_FOR_CLARIFICATION"
    TIMED_OUT = "TIMED_OUT"

class AgentState(TypedDict):
    """
    Strongly typed shared state for the multi-agent graph execution.
    """
    request_id: str
    user_id: str
    workspace_id: str
    conversation_id: str
    original_prompt: str
    current_task: Optional[str]
    execution_status: ExecutionStatus
    execution_plan: Optional[List[str]]
    detailed_execution_plan: Optional[Dict[str, Any]]
    messages: List[Dict[str, Any]]
    agent_outputs: Dict[str, Any]
    tool_results: List[Dict[str, Any]]
    memory_context: Optional[str]
    memory_results: Optional[Dict[str, Any]]
    research_results: Optional[str]
    critic_result: Optional[str]
    critic_decision: Optional[str]
    quality_score: Optional[Dict[str, Any]]
    final_response: Optional[str]
    errors: List[str]
    metadata: Dict[str, Any]
    timestamps: Dict[str, str]
    token_usage: Dict[str, int]
    execution_time: float
    confidence_score: float
    current_agent: Optional[str]
    retry_count: int
