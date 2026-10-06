# AegisAI Enterprise — Phase 12.11: Demo / Showcase Mode Specification

## 1. Executive Summary & Objective

**Phase 12.11** establishes a presentation layer called the **AegisAI Showcase & Demo Mode** (`/showcase` and `/demo`).

The system enables deterministic, controlled demonstration of AegisAI's multi-agent capabilities for project presentations, hackathons, stakeholder walkthroughs, and technical evaluations without touching production data, mutating real workspaces, bypassing authentication or RBAC boundaries, or exposing credentials.

---

## 2. Core Design Principles & Safety Guarantees

1. **Zero Confusion with Real Data**:
   - Every simulated view, event, and document is explicitly tagged with `DEMO`, `SIMULATED`, or `SHOWCASE`.
   - A persistent, non-dismissible amber banner appears across all showcase views:
     > `DEMO MODE :: Simulated Presentation Environment — No production data or actions are modified.`
2. **Zero Production Mutation**:
   - All scenario steps execute strictly in-memory within the frontend presentation orchestrator.
   - Zero HTTP `POST`/`PUT`/`DELETE` calls are made to live production workspaces or administrative configurations.
3. **Zero Hardcoded Secrets / Credentials**:
   - Any security or authorization tokens demonstrated in simulated events use explicit `[REDACTED — DEMO]` or synthetic hashes.
4. **Isolated Synthetic Context**:
   - Synthetic Enterprise Entity: **Aegis Logistics Enterprise** (`Aegis-Demo` tenant).
   - Facilities: Mumbai Distribution Hub, Ahmedabad Bio-Pharma Vault, Bengaluru Operations Center.

---

## 3. Showcase Architecture & Component Map

```
ShowcasePage (/showcase, /demo)
├── DemoBanner (Persistent warning, scenario badge, synthetic tenant tag, exit button)
├── Master Header (Controls, speed multiplier, presentation mode toggle, theme switcher)
├── Sub-Navigation Bar (Scenarios, Architecture Map, 9-Station Guided Tour, Elapsed Timer)
│
├── View 1: Interactive Scenarios
│   ├── Scenario Selector Cards (5 categorized scenarios with duration & difficulty)
│   ├── Active Scenario Card (Business problem, prompt, systems involved, controls)
│   ├── DemoTimeline (8-stage execution bar: Request -> Understand -> Plan -> Retrieve -> Reason -> Execute -> Verify -> Respond)
│   ├── Main Stage Output Split View:
│   │   ├── Active Agent Node Card (Stage number, agent name, operation detail)
│   │   ├── DemoEventStream (Live simulated event log with timestamps and role tags)
│   │   └── Final Verified Response Panel (Answer, Key Findings, Reasoning Summary, Next Actions)
│   └── DemoEvidenceViewer (3 Grounding Citations + 7-Node SVG Knowledge Graph)
│
├── View 2: System Architecture Map (User -> AI OS -> 9-Agent Swarm -> Knowledge/MCP -> Governance -> Evidence)
│   └── Interactive Legend (Real Platform Components vs Simulated Demo Events)
│
├── View 3: 9-Station Guided Tour (Carousel & detailed walkthrough of the 9 core subsystems)
│
└── DemoApprovalModal (Simulated Human-in-the-Loop Dual-Key Governance Authorization Gate)
```

---

## 4. Deterministic Scenario Registry

| Scenario ID | Title | Category | Duration | Demonstrated Subsystems | Key Highlights |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `flagship-coldchain` | **End-to-End Cold-Chain Investigation** | Flagship Journey | 45s | Orchestrator, Planner, Enterprise RAG, Knowledge Graph, MCP Runner, Critic, Response Engine | Cross-references SOP threshold (>10°C / >30m) with sensor telemetry (11.2°C / 42m) on Shipment SH-2048 to trigger protocol escalation. |
| `autonomous-workflow` | **Autonomous Multi-Agent Workflow Studio** | Workflows | 30s | Visual Workflow Studio, Research Agent, RAG Agent, Condition Node, Critic Node | Ingests 14,200 warehouse inventory records, verifies discrepancy threshold (0.003% vs 1.00%), and compiles compliance report. |
| `controlled-failure` | **Fault Tolerance & Tool Fallback Recovery** | Resilience | 30s | Orchestrator, Tool Executor, Critic Agent, Secondary Satellite Cache | Simulates a primary MCP tool timeout (HTTP 504), diagnosed by Critic, which seamlessly routes to secondary satellite cache. |
| `security-guardrail` | **Prompt Injection Defense & Guardrail Gate** | Security | 25s | Security Guardrail, Input Sanitizer, Orchestrator, Audit Logger | Ingests untrusted document with hidden injection directive ("IGNORE ALL PREVIOUS INSTRUCTIONS"), intercepts and quarantines the attack. |
| `governance-approval` | **High-Risk Action Dual-Key Governance Approval** | Governance | 30s | Governance Control Plane, RBAC Policy Engine, Human Operator, Audit Ledger | Triggers interactive Human-in-the-Loop approval modal for thermal override on Ahmedabad Vault, requiring rationale before execution. |

---

## 5. Presentation Mode & Controls

- **Speed Multipliers**:
  - `1x` (Normal): ~1200ms per stage (natural pacing).
  - `2x` (Fast): ~600ms per stage (accelerated review).
  - `Instant` (Presentation): ~250ms per stage (rapid execution for live talks).
- **Playback Controls**:
  - `Start Demo` / `Pause Demo` / `Replay Demo`: Toggles execution stream.
  - `Skip Step`: Manually advances to the next execution stage.
  - `Reset`: Clears state back to Step 1 without modifying session state.
- **Presentation View**:
  - Toggled via top-right maximize icon.
  - Hides auxiliary navigation bars to focus entirely on the scenario timeline, active agent reasoning, and evidence verification.

---

## 6. Verification & Test Coverage

- **Vitest Unit & Integration Tests**: 15 test suites passed, **223/223 tests passed (100%)** (+17 tests in `demo_showcase.test.jsx`).
- **Vite Production Build**: 2,572 modules transformed cleanly in 1.45s with `ShowcasePage` isolated into a 54.42 kB chunk.
- **Pytest Backend Regression**: **955/955 tests passing (100%)**.
- **Automated Browser E2E**: `NOT BROWSER-VERIFIED` (Headless browser automation was not executed in this environment).
