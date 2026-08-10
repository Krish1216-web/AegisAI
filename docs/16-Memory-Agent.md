# 16. Memory Agent

The **Memory Agent** manages retrieval, relevance ranking, and selective writing of isolated tenant memories across sessions.

---

## 1. Retrieval Lifecycle

```text
User prompt and context
         ↓
    Memory Agent
  ├── Tenant Isolation Check (user_id & workspace_id verification)
  └── Query Construction
         ↓
BaseMemoryProvider (search / store / update / delete / get)
         │
         ├── MockMemoryProvider (In-memory, word matching ranker)
         └── Future Providers (PostgreSQL pgvector, Qdrant, Chroma)
         ↓
   Retrieved Memory Records
         ↓
  AIService consolidation (Synthesizes memory context string)
         ↓
   MemoryResult + Context update to AgentState
```

---

## 2. Pydantic Models

```python
class MemoryType(str, Enum):
    SESSION = "SESSION"
    CONVERSATION = "CONVERSATION"
    USER_PREFERENCE = "USER_PREFERENCE"
    USER_FACT = "USER_FACT"
    TASK_HISTORY = "TASK_HISTORY"
    DOCUMENT_CONTEXT = "DOCUMENT_CONTEXT"
    LEARNING = "LEARNING"
    PROJECT_CONTEXT = "PROJECT_CONTEXT"
    SYSTEM_KNOWLEDGE = "SYSTEM_KNOWLEDGE"

class MemoryRecord(BaseModel):
    memory_id: str
    user_id: str
    workspace_id: str
    memory_type: MemoryType
    content: str
    source: str
    importance: float
    confidence: float
    created_at: str
    updated_at: str
    expires_at: Optional[str]
    tags: List[str]
    metadata: Dict[str, Any]
```

---

## 3. Strict Tenant Isolation
To prevent cross-tenant information leaks, all query executions require explicit `user_id` and `workspace_id` matching. If these attributes are absent or mismatched:
- Search returns an empty result.
- GET and CRUD mutations raise a `MemoryPermissionError`.

---

## 4. Privacy Filter (Secret Scrubbing)
A deterministic regex scrubbing layer `scrub_sensitive_data` matches passwords, secrets, open keys, and private tokens inside retrieved context content before writing to state, replacing matches with a `[REDACTED_SECRET]` placeholder.

---

## 5. Run Tests
Run the test suite:
```bash
python -m pytest backend/tests/unit/test_memory.py
```
This tests CRUD functionality, user/workspace boundaries, credential scrubbing, and Orchestrator-Planner-Memory pipeline integration.
