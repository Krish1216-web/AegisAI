# Contributing to AegisAI

Thank you for your interest in contributing to **AegisAI**! We are committed to building a reliable, secure, and performant enterprise autonomous multi-agent platform.

---

## 🏛️ Code of Conduct & Development Principles

When contributing to AegisAI, please adhere to our core engineering principles:

1. **Truth-First Implementation**: Never write placeholder stubs that pretend to execute actions. All features, agents, and tools must either execute real logic or return structured, typed errors.
2. **Strict Multi-Tenant Isolation**: Every database query, vector search, file access, and memory lookup must be scoped by `workspace_id` and verified against user credentials.
3. **No Secret Leaks**: Never commit API keys, private tokens, passwords, or encryption salts. Use environment variables and mock providers for testing.
4. **Comprehensive Test Coverage**: Any new feature or bug fix must include corresponding unit and integration tests in `backend/tests/` (Pytest) and/or `frontend/src/__tests__/` (Vitest).

---

## 🛠️ Development Setup

### 1. Fork & Clone Repository
```bash
git clone https://github.com/KrishPatel/AegisAI.git
cd AegisAI
```

### 2. Backend Environment
```bash
cd backend
python -m venv venv
# Activate virtual environment:
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
cp ../.env.example .env
alembic upgrade head
```

### 3. Frontend Environment
```bash
cd ../frontend
npm install
cp .env.example .env
```

---

## 🧪 Running Local Verification

Before submitting any Pull Request, ensure that all automated test suites pass cleanly:

```bash
# 1. Run all backend tests (Target: 100% pass)
cd backend
pytest -q

# 2. Run all frontend tests (Target: 100% pass)
cd ../frontend
npm test -- --run

# 3. Verify production Vite build (Target: 0 errors)
npm run build
```

---

## 🌿 Branching Strategy & Git Workflow

- Main development branches follow the naming convention:
  - `feat/<feature-name>`: New capabilities or architectural modules.
  - `fix/<issue-name>`: Bug fixes and security patches.
  - `docs/<doc-name>`: Documentation updates and architectural guides.
  - `perf/<perf-name>`: Performance and accessibility optimizations.
- Commit messages should follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:
  - `feat: add hybrid search reranking to enterprise RAG`
  - `fix: prevent race condition in workflow node state machine`
  - `docs: update knowledge graph schema reference`
  - `test: add fuzzing suite for MCP JSON-RPC payloads`

---

## 📋 Pull Request Checklist

Before opening a PR, verify the following:
- [ ] Code adheres to PEP 8 (Python) and ESLint/Prettier (JavaScript/React).
- [ ] No hardcoded secrets or environment values.
- [ ] All database changes include a migration script (`alembic revision --autogenerate`).
- [ ] Backend tests pass (`pytest -q`).
- [ ] Frontend tests pass (`npm test -- --run`).
- [ ] Documentation is updated in `docs/` or `frontend/docs/` if architectural behavior changed.
