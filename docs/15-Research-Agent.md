# 15. Research Agent

The **Research Agent** gathers, analyzes, and consolidates raw search information, maps assertions to distinct findings, and compiles evidence matrices linking findings to retrieved sources.

---

## 1. Research Lifecycle

```text
Planner execution plan
         ↓
  Research Agent (Query normalization & truncation check)
         ↓
BaseResearchProvider (search / retrieve abstraction)
         │
         ├── MockResearchProvider (development / testing data)
         └── Future Providers (Web Search, Browser MCP, Enterprise DB)
         ↓
    Raw Sources Content
         ↓
 AIService consolidation (Synthesis and fact-linking prompt)
         ↓
  ResearchResult (Pydantic validated list of findings + sources)
```

---

## 2. Research Models

```python
class ResearchSource(BaseModel):
    source_id: str
    title: str
    url: Optional[str]
    source_type: str
    publisher: Optional[str]
    published_at: Optional[str]
    retrieved_at: str
    relevance_score: float
    content_reference: str

class ResearchFinding(BaseModel):
    finding_id: str
    title: str
    claim: str
    supporting_evidence: str
    source_ids: List[str]
    confidence: float
    relevance: float
    timestamp: str

class ResearchResult(BaseModel):
    query: str
    summary: str
    findings: List[ResearchFinding]
    sources: List[ResearchSource]
    confidence: float
    research_time: float
    source_count: int
    limitations: List[str]
```

---

## 3. Evidence Linking
To prevent hallucinations and unbacked citations, the Research Agent verifies that every referenced `source_id` within a `ResearchFinding` matches an existing, retrieved `ResearchSource`. Invalid references trigger an `InvalidResearchResult` exception.

---

## 4. MCP and Future Extensions
The `BaseResearchProvider` interface isolates client-specific search code. Future integrations (e.g. Brave Search MCP, Google Search API, local vector database document retrievals) can be connected by implementing the class:
```python
class BraveSearchMCPProvider(BaseResearchProvider):
    # Implement Brave search APIs
```

---

## 5. Run Tests
Execute the unit test suite:
```bash
python -m pytest backend/tests/unit/test_research.py
```
This tests MockProvider data retrieval, source-linking validations, query limits, and Orchestrator-Planner-Research chained integration.
