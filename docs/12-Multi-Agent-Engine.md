# 12. Multi-Agent Engine Foundation

AegisAI coordinates complex, multi-agent activities using a custom graph orchestration pipeline built on LangGraph.

---

## 1. Graph State Model
The shared state dict `AgentState` holds transaction histories, execution timelines, tokens, and agent communication channels.

```python
class AgentState(TypedDict):
    request_id: str
    user_id: str
    workspace_id: str
    conversation_id: str
    original_prompt: str
    current_task: Optional[str]
    execution_status: ExecutionStatus
    execution_plan: Optional[List[str]]
    messages: List[Dict[str, Any]]
    agent_outputs: Dict[str, Any]
    tool_results: List[Dict[str, Any]]
    final_response: Optional[str]
    errors: List[str]
    token_usage: Dict[str, int]
    execution_time: float
    confidence_score: float
    current_agent: Optional[str]
    retry_count: int
```

---

## 2. Reusable Agent Interface
Every specialized AegisAI agent implements the `BaseAgent` abstract class:

```python
class BaseAgent(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str: pass

    @abc.abstractmethod
    async def execute(self, state: AgentState, context: ExecutionContext) -> AgentResult: pass

    @abc.abstractmethod
    def validate_input(self, state: AgentState) -> bool: pass

    @abc.abstractmethod
    def validate_output(self, result: AgentResult) -> bool: pass
```

---

## 3. Execution Status Flow
Agent states change according to the following lifecycle enums:

`PENDING` → `PLANNING` → `RESEARCHING` → `MEMORY_RETRIEVAL` → `TOOL_EXECUTION` → `CRITIC_REVIEW` → `GENERATING_RESPONSE` → `COMPLETED` | `FAILED`

---

## 4. Checkpointing & Recovery
The `BaseCheckpointer` abstract class defines hooks for backing up execution progress. The default `InMemoryCheckpointer` writes snapshots into local key-value stores indexed by `execution_id`, supporting rollbacks and resume capabilities.

---

## 5. Testing
Run tests using:
```bash
python -m pytest backend/tests/unit/test_agent_engine.py
```
This tests node compilation, state transitions, validation failures, and checkpoint recovery without requiring active LLM provider keys.
