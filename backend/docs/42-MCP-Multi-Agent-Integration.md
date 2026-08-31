# Phase 6.7: MCP + Multi-Agent Integration Architecture

## Overview
Phase 6.7 completes the integration of Model Context Protocol (MCP) capabilities directly into the existing LangGraph multi-agent cognitive architecture of AegisAI. External tools, workspace resources, and prompt templates are now first-class capability sources alongside local tools, RAG document retrieval, Knowledge Graph reasoning, web research, and conversational memory.

---

## 1. Multi-Agent MCP Flow Architecture

```mermaid
graph TD
    User([User Request]) --> Orch[OrchestratorAgent]
    Orch -->|ExecutionPlan: requires_mcp=True| Plan[PlannerAgent]
    Plan -->|PlanStep: tool_source='MCP'| Exec[ToolExecutorAgent]
    
    subgraph Execution Coordination
        Exec --> Sec[MCPSecurityService]
        Sec -->|Allow & Safe| ToolSvc[MCPToolExecutionService / MCPResourceService / MCPPromptService]
        Sec -->|Restricted & No Token| Conf[ToolConfirmationRequired]
        ToolSvc --> San[Sanitization & UNTRUSTED_MCP Label]
    end
    
    Exec --> Critic[CriticAgent]
    Critic -->|Validate Provenance & Anti-Fabrication| Resp[ResponseGeneratorAgent]
    Resp -->|Structured Attribution: [MCP Tool/Resource]| Out([Final Grounded Response])
```

---

## 2. Agent Responsibilities in MCP Execution

### A. OrchestratorAgent
- **Task Classification**: Evaluates user prompts for external MCP tools (`TaskType.MCP_TOOL`), workspace resource inspection (`TaskType.MCP_RESOURCE`), prompt template rendering (`TaskType.MCP_PROMPT`), and cross-source comparisons (`TaskType.MCP_HYBRID`).
- **Execution Plan Enrichment**: Sets `requires_mcp=True`, `mcp_operation="tool"|"resource"|"prompt"|"hybrid"`, and selects required agents (`AgentType.TOOL_EXECUTOR`).

### B. PlannerAgent
- **Step Decomposition**: Emits `PlanStep` with `tool_source="MCP"`, `capability_type="TOOL"|"RESOURCE"|"PROMPT"`, `action="mcp:<name>"`, and optional `tool_id`.
- **Security Boundary**: Planner output remains untrusted; it does not grant permissions or bypass validation. All steps are re-validated by backend execution services.

### C. ToolExecutorAgent
- **MCP Tool Execution**: Resolves capability from catalog and invokes `MCPToolExecutionService.execute_tool`.
- **MCP Resource Reading**: Discovers and reads workspace resources via `MCPResourceService.read_resource`, attaching `UNTRUSTED_MCP` trust labels and populating `state["mcp_resource_context"]`.
- **MCP Prompt Rendering**: Renders parameterized prompt templates via `MCPPromptService.render_prompt` and populates `state["mcp_prompt_context"]`.
- **Confirmation Gating**: Enforces cryptographically bound single-use confirmation tokens for `RESTRICTED` tools.

### D. CriticAgent
- **Provenance & Integrity Validation**: Verifies that tool outputs, resource URIs, and prompt templates correspond to valid server and capability IDs.
- **Anti-Fabrication & Tenant Isolation**: Rejects fabricated citations and cross-tenant leaks with `CriticDecision.FAIL`.

### E. ResponseGeneratorAgent
- **Source Attribution**: Synthesizes final responses with explicit source tagging:
  - `[MCP Tool: <name>]`
  - `[MCP Resource: <title>]`
  - `[MCP Prompt: <name>]`
  - `[Document: <name>]`
  - `[Knowledge Graph: <entity>]`
  - `[Research: <source>]`

---

## 3. Real-Time Streaming SSE Events
The pipeline logs dedicated MCP SSE events to Redis streams (`aegis:stream:<execution_id>`):
- `MCP_DISCOVERY_STARTED` / `MCP_DISCOVERY_COMPLETED`
- `MCP_TOOL_PLANNED`
- `MCP_TOOL_STARTED` / `MCP_TOOL_COMPLETED` / `MCP_TOOL_FAILED`
- `MCP_TOOL_CONFIRMATION_REQUIRED`
- `MCP_RESOURCE_STARTED` / `MCP_RESOURCE_COMPLETED` / `MCP_RESOURCE_FAILED`
- `MCP_PROMPT_STARTED` / `MCP_PROMPT_COMPLETED` / `MCP_PROMPT_FAILED`
- `MCP_SECURITY_DENIED`

---

## 4. Verification & Testing
- **15 new dedicated unit tests**:
  - `backend/tests/unit/test_mcp_orchestrator.py`
  - `backend/tests/unit/test_mcp_planner.py`
  - `backend/tests/unit/test_mcp_agent_integration.py`
  - `backend/tests/unit/test_mcp_pipeline.py`
- **Full test suite passing**: 294 / 294 unit tests passing (100%).
- **Frontend production build**: passing without warnings.
