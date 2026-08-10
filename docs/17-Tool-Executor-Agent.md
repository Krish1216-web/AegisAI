# 17. Tool Executor Agent

The **Tool Executor Agent** manages the safe registration, argument validation, and execution of approved tools mapped from Planner steps.

---

## 1. Tool Execution Pipeline

```text
Planner step definition (agent_type: TOOL_EXECUTOR)
                       ↓
              ToolExecutorAgent
  ├── Resolve action target (Calculator, Weather, etc.)
  ├── Idempotency verification (Duplicate execution check)
  ├── Required permission guard check (RBAC match)
  ├── Schema validation (Argument type and limit constraints)
  └── Confirmation check (Binds tokens to high-risk actions)
                       ↓
                 BaseTool run
                       ↓
ToolExecutionResult (Status: SUCCESS, FAILED, TIMEOUT, DENIED, etc.)
```

---

## 2. Models & Tokens

```python
class ToolDefinition(BaseModel):
    tool_id: str
    name: str
    description: str
    category: ToolCategory
    version: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    required_permissions: List[str]
    risk_level: RiskLevel
    requires_confirmation: bool
    enabled: bool

class ToolExecutionResult(BaseModel):
    execution_id: str
    tool_id: str
    status: ToolExecutionStatus
    output: Optional[Dict[str, Any]]
    error: Optional[str]
    execution_time: float
```

### Confirmation Token Generator
High-risk tools (e.g. Risk Level: `HIGH` or `CRITICAL`) require explicit human confirmation. The executor binds confirmation tokens securely to execution boundaries:
```python
hash = sha256(execution_id + tool_id + user_id + workspace_id + sha256(arguments))
```

---

## 3. Idempotency & Safety
- **Idempotency**: Prevents duplicate executions of side effects (like sending emails) by checking the request's `execution_id`. Mismatches raise a `ToolAlreadyExecuted` exception.
- **Safety**: Code execution blocks access to `eval()` or OS shell commands.

---

## 4. Run Tests
Run the test suite:
```bash
python -m pytest backend/tests/unit/test_executor.py
```
This tests registration, calculator operations, isolation barriers, token generations, idempotency checks, and Orchestrator-Planner-Executor integration.
