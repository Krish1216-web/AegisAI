# End-to-End Execution Flow

This document maps out the sequence trace of a user query submitted from the workspace chat through backend orchestration nodes down to streaming SSE results.

---

## 1. Trace Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as Workspace User
    participant FE as Frontend Client
    participant BE as FastAPI Gateway
    participant DB as PostgreSQL DB
    participant RD as Redis Cache
    participant AG as LangGraph multi-agent pipeline

    User->>FE: Submits query prompt
    FE->>BE: POST /agent/execute/stream (with Bearer Token + Workspace ID)
    activate BE
    BE->>DB: Validate user workspace membership
    BE->>RD: Set execution lock: aegis:execution:{execution_id}
    
    par Stream Reader
        BE-->>FE: Stream started headers
    and Graph Execution
        BE->>AG: Compile graph and execute(initial_state)
        activate AG
        AG->>RD: Publish ORCHESTRATOR_STARTED
        RD-->>FE: SSE line: data: {event: ORCHESTRATOR_STARTED}
        
        AG->>AG: Execute PlannerAgent
        AG->>RD: Publish PLANNER_STARTED
        RD-->>FE: SSE line: data: {event: PLANNER_STARTED}

        AG->>AG: Execute ResearchAgent (Tavily search)
        AG->>RD: Publish RESEARCH_STARTED
        RD-->>FE: SSE line: data: {event: RESEARCH_STARTED}
        
        AG->>AG: Execute ToolExecutorAgent
        AG->>RD: Publish TOOL_STARTED
        RD-->>FE: SSE line: data: {event: TOOL_STARTED}
        
        AG->>AG: Execute CriticAgent (Deterministic check)
        AG->>RD: Publish CRITIC_STARTED
        RD-->>FE: SSE line: data: {event: CRITIC_STARTED}

        AG->>AG: Execute ResponseGeneratorAgent (Sanitizer)
        AG->>RD: Publish RESPONSE_GENERATING
        RD-->>FE: SSE line: data: {event: RESPONSE_GENERATING}
        
        AG->>DB: Save run checkpoint & execution events
        AG->>RD: Publish EXECUTION_COMPLETED
        RD-->>FE: SSE line: data: {event: EXECUTION_COMPLETED}
        deactivate AG
    end
    
    BE->>RD: Release lock: aegis:execution:{execution_id}
    deactivate BE
    FE->>User: Displays final response
```

---

## 2. Cancellation Event Flow
1. User presses **STOP** in the UI.
2. Frontend dispatches `POST /agent/executions/{id}/cancel`.
3. Backend registers signal `aegis:cancel:{id}` inside Redis.
4. Next node evaluates the lock. If cancelled, it halts executions and publishes `EXECUTION_CANCELLED` to the client.

---

## 3. Human Confirmation Flow
1. Tool Executor requires confirmation for a high-risk tool execution.
2. Backend returns `WAITING_FOR_CONFIRMATION` event with a one-time token.
3. Frontend shows confirmation overlay (Approve/Deny).
4. User clicks **Approve**, sending `POST /agent/executions/{id}/confirm` containing the token.
5. Backend verifies token, executes tool, and resumes.
