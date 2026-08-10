# 18. Critic Agent

The **Critic Agent** evaluates the output quality, plan adherence, and safety dimensions of multi-agent activities before allowing final user response generation.

---

## 1. Review & Routing Lifecycle

```text
Completed state elements (Research results, memory context, tool results)
                               ↓
                        CriticAgent
  ├── Safety check (API credentials, cross-user isolation leaks)
  ├── Adherence check (Satisfies dependencies and limits)
  └── Quality scores calculation (Deterministically mapped overall score)
                               ↓
                   CriticResult (decision outcome)
                               │
       ┌───────────────────────┼────────────────────────┐
       ▼                       ▼                        ▼
    ACCEPT                   RETRY                 RESEARCH_MORE
       ↓                       ↓                        ↓
Response Generator        PlannerAgent            ResearchAgent
```

---

## 2. Quality Dimensions & Scoring
The Critic rates execution across nine distinct dimensions:
- `completeness`
- `correctness`
- `relevance`
- `evidence_coverage`
- `plan_adherence`
- `tool_validity`
- `memory_relevance`
- `consistency`
- `safety`

All dimension metrics must range strictly between `0.0` and `1.0`. The overall score is calculated as a deterministic average of these dimensions.

---

## 3. Safety Auditing & Isolation Guards
If the Critic detects any of the following safety issues, it overrides LLM output and enforces a `FAIL` decision:
- **Tenant Mismatches**: Cross-user/workspace memory data present in contexts.
- **Unconfirmed Executions**: High-risk tool calls executed without matching confirmation tokens.
- **Exposure**: API keys or password strings in raw text results.

---

## 4. Loop Protection
To prevent infinite multi-agent execution loops:
- The Critic increments the state's `retry_count` metrics on `RETRY` decisions.
- If `retry_count >= 3`, the Critic forces a `FAIL` decision and terminates execution.

---

## 5. Run Tests
Run the test suite:
```bash
python -m pytest backend/tests/unit/test_critic.py
```
This tests mock evaluations, security leak rejection, tool failures, loop protection, and full Orchestrator-Planner-Critic integration runs.
