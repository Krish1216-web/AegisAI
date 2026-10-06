# AegisAI — Testing Strategy & Comprehensive Test Inventory

## 1. Testing Philosophy & Verification Standard

AegisAI maintains a rigorous automated testing standard covering unit, integration, boundary fuzzing, security isolation, and frontend UI components. **Every build is verified with 100% test pass rates across both backend and frontend environments.**

```
==================================================================================
TOTAL VERIFIED LOCAL AUTOMATED TESTS: 1,178 PASSING (100%)
- Backend Pytest Suite: 955 Passed (0 Failed, 0 Skipped)
- Frontend Vitest Suite: 223 Passed (0 Failed, 0 Skipped across 15 test suites)
- Frontend Production Build: 2,572 modules transformed cleanly (0 errors)
==================================================================================
```

---

## 2. Test Execution Commands

### 2.1 Backend Pytest Execution
```bash
cd backend

# Execute complete test suite
pytest -q

# Execute with verbose output and duration profiling
pytest -v --durations=10

# Execute specific test domain
pytest tests/unit/test_platform_execution.py -v
pytest tests/unit/test_mcp_*.py -v
pytest tests/unit/test_workflow_*.py -v
```

### 2.2 Frontend Vitest Execution
```bash
cd frontend

# Execute complete test suite once
npm test -- --run

# Execute in interactive watch mode during development
npm test

# Verify production Vite build and bundle output
npm run build
```

---

## 3. Backend Test Suite Inventory (955 Tests)

| Test Category | Primary Test Files | Test Count | Key Invariants Verified |
| :--- | :--- | :--- | :--- |
| **Authentication & Sessions** | `test_auth_*.py`, `test_authentication_session_security.py` | 74 | JWT verification, refresh rotation, expiration, password hashing (bcrypt). |
| **RBAC & Multi-Tenancy** | `test_roles_*.py`, `test_teams_*.py`, `test_tenant_isolation_*.py` | 118 | Workspace boundaries, effective permissions, role elevation blocks. |
| **Multi-Agent Engine** | `test_platform_execution.py`, `test_platform_intelligence_*.py`, `test_agent_*.py` | 142 | State machine transitions, DAG planning, critic verification, synthesis. |
| **Memory Vault** | `test_memory_*.py`, `test_memory_graph_sync.py` | 82 | Vector cosine recall, TTL session eviction, memory-graph synchronization. |
| **Enterprise RAG** | `test_document_*.py`, `test_chunking_embeddings.py`, `test_rag_service.py` | 94 | PDF/DOCX/TXT extraction, sliding-window chunking, citation offsets. |
| **Knowledge Graph** | `test_knowledge_graph_*.py`, `test_graph_rag_enhancement.py` | 68 | Triple CRUD, BFS shortest-path reasoning, subgraph serialization. |
| **MCP Integration** | `test_mcp_*.py`, `test_mcp_security_threat_model.py` | 112 | SSE, HTTP, STDIO, WS transports, schema validation, SSRF filters. |
| **Visual Workflows** | `test_workflow_*.py`, `test_advanced_conditions_routing.py` | 128 | DAG execution, Kahn's cycle detection, variables, human approval queues. |
| **Admin & Audit Governance** | `test_platform_admin_*.py`, `test_compliance_readiness.py` | 78 | SHA-256 audit hash chaining, secret redaction, compliance CSV export. |
| **Security & Fuzzing** | `test_secrets_ssrf_ai_security.py`, `test_automated_security_testing_fuzzing.py` | 59 | Boundary payloads, invalid JSON, SQL injection attempts, rate limits. |

---

## 4. Frontend Vitest Inventory (223 Tests across 15 Suites)

| Test Suite File | Test Count | Primary Coverage Scope |
| :--- | :--- | :--- |
| `performance_accessibility.test.jsx` | 42 | ARIA attributes, keyboard traps, focus loops, dynamic chunk imports, theme switches. |
| `design_system.test.jsx` | 22 | Design token fidelity, badge/button variants, responsive typography, color contrasts. |
| `agent_center.test.jsx` | 17 | Category filtering, agent inspection drawer, DAG topology view, comparison view. |
| `demo_showcase.test.jsx` | 17 | Showcase scenario playback, speed controls, persistent demo indicator, step skipping. |
| `landing_factory.test.jsx` | 16 | Top navigation, interactive tour stations, CTA routing, theme toggles. |
| `workflow_builder.test.jsx` | 13 | Canvas rendering, node palette, cycle detection, variable modal, execution logs. |
| `knowledge_intelligence.test.jsx` | 12 | Document uploads, RAG search, citation drawer, 2D force graph, BFS pathfinder. |
| `user_journeys.test.jsx` | 4 | Complete user workflow flows (chat -> document -> workflow execution). |
| `api_client.test.js` | 3 | Axios/fetch interceptors, JWT attachment, token refresh on 401. |
| `auth_and_session.test.jsx` | 3 | Login state persistence, logout cleanup, protected route guards. |
| `browser_security.test.jsx` | 2 | Secure cookie handling and XSS prevention. |

---

## 5. Mocking & Isolation Strategy

1. **Deterministic Unit Tests**: External LLM network requests and third-party APIs are replaced with deterministic mock providers in unit suites to prevent test flakiness and cost accumulation.
2. **In-Memory SQLite / Mock DB**: Unit tests run against isolated in-memory transaction rollbacks, ensuring tests do not leave residual data or depend on pre-existing database state.
3. **Vitest JSDOM Emulation**: Frontend tests emulate browser DOM environments with mock ResizeObserver, IntersectionObserver, and SVG canvas measurement stubs.
