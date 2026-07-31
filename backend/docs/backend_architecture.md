# AegisAI - Backend Folder Structure & Project Organization

This specification details the production-ready backend project organization, module responsibilities, coding conventions, and folder hierarchy for **AegisAI**.

---

## 1. Directory Hierarchy

The project implements a **Clean Architecture** layout combined with the **Service Layer** and **Repository Pattern**.

```
backend/
├── alembic/                    # database migration revisions
├── docker/                     # service dockerfiles
│   ├── app.dockerfile
│   ├── worker.dockerfile
│   └── mcp_proxy.dockerfile
├── docs/                       # architecture & api specifications
├── scripts/                    # migration & database seed utilities
├── requirements/               # split dependency locks
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── tests/                      # test suite
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   ├── api/
│   ├── agents/
│   ├── memory/
│   └── mcp/
├── app/                        # main application packaging
│   ├── api/                    # controllers & HTTP routing endpoints
│   │   ├── v1/
│   │   └── dependencies.py
│   ├── auth/                   # credentials validation & RBAC checkers
│   ├── core/                   # security parameters, logs & configuration configs
│   ├── database/               # connection pools & base class sessions
│   ├── middleware/             # TLS headers, CORS, rate limits
│   ├── models/                 # SQLAlchemy database schemas
│   ├── schemas/                # Pydantic data schemas
│   ├── repositories/           # raw SQL operations wrappers
│   ├── services/               # clean transactional business services
│   ├── agents/                 # LangGraph multi-agent cognitive graphs
│   │   ├── base/
│   │   ├── orchestrator/
│   │   ├── planner/
│   │   ├── research/
│   │   ├── memory/
│   │   ├── executor/
│   │   └── critic/
│   ├── memory/                 # vector engine integrations (Qdrant)
│   ├── mcp/                    # Model Context Protocol standard gateways
│   ├── workflows/              # Celery pipeline run scripts
│   ├── analytics/              # system telemetry metrics analyzers
│   ├── notifications/          # ws broadcast channels
│   ├── documents/              # file parser modules
│   ├── websocket/              # ws connections manager
│   ├── utils/                  # helpers & algorithms
│   └── main.py                 # entry point
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## 2. Directory Responsibilities

| Directory | Purpose | Responsibility | Prohibited Content |
| :--- | :--- | :--- | :--- |
| `app/api/` | Exposes HTTP routes. | Maps JSON HTTP requests directly to service handlers. | Business logic, raw SQL, direct LLM API invocations. |
| `app/services/` | Transaction boundaries. | Combines database writes, external calls, and file transformations. | Database drivers connection parameters, raw JSON mapping. |
| `app/repositories/` | Decouples ORM database writes. | Implements SQL database transactions using SQLAlchemy. | Web parameters, session attributes, agent state blocks. |
| `app/agents/` | Orchestrates cognitive execution. | Designs cycle-breakers, planner graphs, and critic validators. | Direct SQL inserts, filesystem writes, API keys. |
| `app/mcp/` | Integrates tool bridges. | standardizes tool bindings and manages connection sessions. | Application business transactions, local workspace states. |

---

## 3. Python Coding Standards

### Naming Conventions
- **Folder Names**: All lowercase, no special characters, underscores strictly limited (e.g., `repositories`, `mcp`).
- **Python File Names**: snake_case (e.g., `user_service.py`, `mcp_client.py`).
- **Class Names**: CamelCase (e.g., `BaseRepository`, `PlannerAgent`).
- **Function/Method Names**: snake_case (e.g., `retrieve_context()`, `verify_jwt()`).
- **Constants**: UPPERCASE_SNAKE (e.g., `MAX_RETRY_ATTEMPTS`, `JWT_ALGORITHM`).

### Exception & Validation Handling
- Handlers in `app/api/v1/` raise `HTTPException`.
- Internal services raise domain-specific custom exceptions (e.g., `AegisMemoryVaultError`, `McpConnectionTimeout`).
- Input validation strictly utilizes **Pydantic v2** parsing schemas.

---

## 4. Service Layer Responsibilities

```
                      +-----------------------------+
                      |         FastAPI Route       |
                      +-----------------------------+
                                     |
                                     v
                      +-----------------------------+
                      |       Business Service      |
                      |     (e.g. WorkflowService)  |
                      +-----------------------------+
                                     |
                      +--------------+--------------+
                      |                             |
                      v                             v
       +----------------------------+  +----------------------------+
       |      Repository Tier       |  |       Cognitive Tier       |
       |    (PostgreSQL Storage)    |  |     (LangGraph Agent)      |
       +----------------------------+  +----------------------------+
```

1. **Authentication Service**: Evaluates passwords, yields JWT signatures, validates credentials, and clears Redis session keys.
2. **Conversation Service**: Restores chat threads history parameters, inserts message payloads, and stages context.
3. **Workflow Service**: Allocates task parameters and publishes worker tasks to Celery queues.
4. **Memory Service**: Converts prompt logs into vector formats and retrieves contexts from Qdrant indices.
5. **Agent Service**: Triggers LangGraph nodes execution and processes loop state changes.
6. **MCP Service**: Monitors JSON-RPC socket streams and maps tools definitions to Pydantic objects.

---

## 5. Repository Layer Abstraction

AegisAI implements the **Repository Pattern** to separate database operations from the business services layer. This makes the codebase database-agnostic and simplifies unit testing via mock dependencies.

```python
class BaseRepository:
    # Generic CRUD abstraction interface class
    pass

class UserRepository(BaseRepository):
    # Specialized queries for User records
    pass
```

Specialized repositories are defined for:
- `UserRepository`, `RoleRepository` (RBAC parameters)
- `ConversationRepository`, `MessageRepository` (thread history caches)
- `DocumentRepository` (file attributes metadata)
- `WorkflowRepository`, `TaskRepository` (pipeline schedules)

---

## 6. Agent Module Structure

Agents are structured into dedicated packages:

```
app/agents/
├── base/
│   ├── agent.py                # abstract BaseAgent class interface
│   └── state.py                # Pydantic state schemas for LangGraph
├── orchestrator/
│   └── graph.py                # compiles node execution routing paths
├── planner/
│   └── node.py                 # creates execution step lists
├── research/
│   └── node.py                 # controls document and internet lookups
├── memory/
│   └── node.py                 # processes local vector retrievals
├── executor/
│   └── node.py                 # triggers sandboxed commands & tool runs
└── critic/
    └── node.py                 # audits validation accuracy scores
```

---

## 7. Memory & MCP Sub-Modules

### Memory Module (`app/memory/`)
- `client.py`: Wrapper for Qdrant connection pool.
- `embedder.py`: Handles vector calculation pipelines.
- `retriever.py`: Processes similarity search operations and filters metadata.

### MCP Module (`app/mcp/`)
- `registry.py`: Stores active server schemas and tool parameters.
- `client.py`: Manages WebSocket connections to external daemons.
- `protocol.py`: Handles JSON-RPC message formatting and parsing.
