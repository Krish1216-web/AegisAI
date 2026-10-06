# Final Presentation, Viva & Demo Checklist

Use this operational checklist before presenting **AegisAI** to evaluators, professors, interviewers, or stakeholders.

---

## 📋 1. Pre-Presentation System Verification

- [ ] **Backend Server Active**:
  ```bash
  cd backend
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  # Confirm http://localhost:8000/api/v1/health returns {"status": "ok"}
  ```
- [ ] **Frontend Development Server Active**:
  ```bash
  cd frontend
  npm run dev
  # Confirm http://localhost:5173 loads cleanly
  ```
- [ ] **PostgreSQL Database Connected & Seeded**:
  ```bash
  alembic upgrade head
  python -m app.scripts.seed_db
  ```
- [ ] **Redis Running**: Confirm `redis-cli ping` returns `PONG`.
- [ ] **Test Suites Passing**:
  ```bash
  pytest -q            # 955 passed
  npm test -- --run     # 223 passed
  npm run build         # Clean build
  ```

---

## 🖥️ 2. Browser Tab Preparation (Recommended Order)

1. **Tab 1 — Intelligence Factory Landing Tour**: `http://localhost:5173/` (Introduce problem, pillars, and architecture flow).
2. **Tab 2 — AI OS Workspace**: `http://localhost:5173/user/platform` (Demonstrate multi-agent execution, plan drawer, and citation notes).
3. **Tab 3 — Agent Center**: `http://localhost:5173/user/agents` (Demonstrate 9-agent catalog, live telemetry, and comparison drawer).
4. **Tab 4 — Workflow Studio Canvas**: `http://localhost:5173/user/workflows` (Showcase visual DAG builder, Kahn's cycle detection, and approval gates).
5. **Tab 5 — Knowledge Intelligence & Graph**: `http://localhost:5173/user/documents` & `http://localhost:5173/user/graph` (Showcase RAG semantic chunks and 2D force graph).
6. **Tab 6 — Governance & Audit Ledger**: `http://localhost:5173/admin/governance` (Showcase cryptographic SHA-256 hash chains and one-click integrity verification).
7. **Tab 7 — Interactive Showcase Simulator (Safe Fallback)**: `http://localhost:5173/showcase` (Execute scripted cold-chain, prompt-injection, or governance tours).
8. **Tab 8 — GitHub Repository / Documentation**: `https://github.com/Krish1216-web/AegisAI` / [docs/INDEX.md](file:///D:/CP/AegisAI/docs/INDEX.md).

---

## 🛡️ 3. Safe Fallback & Resilience Strategy

If any live backend service or network connection encounters unexpected latency or provider rate limits:
1. **Switch to Showcase Mode**: Instantly navigate to `http://localhost:5173/showcase`.
2. **Explain the Presentation Isolation**: State clearly to examiners that Showcase Mode runs in a dedicated simulation sandbox with pre-scripted state machines, demonstrating the exact user experience without network dependencies.
3. **Reference Verified Automated Test Logs**: Point to the 1,178 passing test suites in [docs/TESTING.md](file:///D:/CP/AegisAI/docs/TESTING.md) to demonstrate core software verification.

---

## 🎙️ 4. Final Review of Defense Materials

- [ ] Reviewed [docs/VIVA-GUIDE.md](file:///D:/CP/AegisAI/docs/VIVA-GUIDE.md) (Spoken scripts & 42 technical questions).
- [ ] Reviewed [docs/PRESENTATION-SLIDES.md](file:///D:/CP/AegisAI/docs/PRESENTATION-SLIDES.md) (15-slide deck outline).
- [ ] Reviewed [docs/ENGINEERING-CHALLENGES.md](file:///D:/CP/AegisAI/docs/ENGINEERING-CHALLENGES.md) (Technical obstacles & trade-offs).
- [ ] Confirmed zero secrets or hardcoded passwords are open in editor tabs.
