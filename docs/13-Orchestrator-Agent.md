# 13. Orchestrator Agent

The **Orchestrator Agent** is the central coordinator of the AegisAI multi-agent operating system. It parses user prompts, determines execution complexity, requests clarifications when required, and builds structured execution pipelines.

---

## 1. Orchestration Analysis Lifecycle

```text
Incoming User Request
         ↓
Orchestrator Classification (LLM Call)
  ├── Task Type (GENERAL_QA, RESEARCH, CODING, etc.)
  ├── Complexity (SIMPLE, MODERATE, COMPLEX, MULTI_STEP)
  └── Required Agents (PLANNER, RESEARCH, MEMORY, CRITIC, etc.)
         ↓
Structured JSON ExecutionPlan
         ↓
LangGraph Conditional Router
  ├── requires_clarification? → Route to END
  └── next_node_target? → Route to target node
```

---

## 2. Pydantic ExecutionPlan Schema

```python
class ExecutionPlan(BaseModel):
    task_type: TaskType
    complexity: Complexity
    goal: str
    steps: List[str]
    required_agents: List[AgentType]
    requires_memory: bool = False
    requires_research: bool = False
    requires_tools: bool = False
    requires_critic: bool = False
    requires_clarification: bool = False
    clarification_question: Optional[str] = None
    confidence: float
```

---

## 3. Local Mock Testing
When `ExecutionContext.provider == "mock"`, the Orchestrator skips remote API queries and returns a mock plan containing a `RESPONSE_GENERATOR` agent.

---

## 4. Run Tests
Run the unit test suite:
```bash
python -m pytest backend/tests/unit/test_orchestrator.py
```
This tests classification validation, mock execution paths, and routing functions.
