# 19. Response Generator Agent

The **Response Generator Agent** is the final execution boundary of the AegisAI multi-agent operating system. It consumes Critic-validated results and structures user-facing responses.

---

## 1. Response Lifecycle

```text
Validated Execution Context (Critic score, Tool status, Research sources)
                                ↓
                      ResponseGeneratorAgent
  ├── Critic Gate check (Blocks FAIL / pausable outcomes)
  ├── Prompt Injection Defense (DATA classification and filter checks)
  └── Citation Validation (No unauthorized source IDs)
                                ↓
        ResponseGenerationResult (User-facing message text)
```

---

## 2. Pydantic Schemas

```python
class ResponseFormat(str, Enum):
    PLAIN_TEXT = "PLAIN_TEXT"
    MARKDOWN = "MARKDOWN"
    JSON = "JSON"
    TABLE = "TABLE"
    CODE = "CODE"

class ResponseCitation(BaseModel):
    citation_id: str
    title: str
    source_id: str
    url: Optional[str]
    publisher: Optional[str]
    published_at: Optional[str]
    reference_text: Optional[str]

class ResponseGenerationResult(BaseModel):
    execution_id: str
    content: str
    format: ResponseFormat
    summary: str
    citations: List[ResponseCitation]
    confidence: float
    limitations: List[str]
    completed: bool
```

---

## 3. Critic Gates
Prior to generating user text, the agent verifies the Critic's decision outcome:
- **FAIL**: Halts output and yields a safe generic execution failure.
- **REQUEST_CLARIFICATION**: Pauses and asks the user for clarification.
- **RESEARCH_MORE** / **TOOL_RETRY**: Returns appropriate incomplete/action-required responses without triggering tool side effects.

---

## 4. Prompt Injection Defense
To secure content generation, the agent scans user inputs and retrieved source context texts against injection strings (e.g. `"ignore previous instructions"`). If matched, it raises an `UnsafeResponse` exception and rejects final message composition.

---

## 5. Citation Security
Every generated citation's `source_id` is matched against actual retrieved source listings in `ResearchResult`. Any fabricated references cause the generator to raise an `InvalidCitation` exception.

---

## 6. Run Tests
Run the test suite:
```bash
python -m pytest backend/tests/unit/test_response.py
```
This tests format outputs, Critic gates, citation validations, injection defense, and integration pipelines.
