# Local Developer Guide & Engineering Setup

## 1. Local Environment Prerequisites

- **Python**: 3.11, 3.12, or 3.13.
- **Node.js**: 20.x or 22.x LTS.
- **PostgreSQL**: 16+ (or run via Docker).
- **Redis**: 7+ (or run via Docker).
- **Git**: 2.40+.

---

## 2. Step-by-Step Developer Setup

### 2.1 Backend Setup
```bash
# 1. Navigate to backend directory
cd backend

# 2. Create virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure local environment
cp ../.env.example .env

# 5. Apply migrations and seed sample workspace
alembic upgrade head
python -m app.scripts.seed_db

# 6. Start development server with reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2.2 Frontend Setup
```bash
# 1. Navigate to frontend directory
cd ../frontend

# 2. Install dependencies
npm install

# 3. Configure frontend environment
cp .env.example .env

# 4. Start Vite development server
npm run dev
```

---

## 3. Recommended Developer Tooling

- **API Documentation**: Interactive Swagger UI at `http://localhost:8000/docs` and Redoc at `http://localhost:8000/redoc`.
- **Database GUI**: Recommended pgAdmin 4 or DBeaver connecting to `localhost:5432/aegisai_db`.
- **Redis CLI**: `redis-cli ping` to confirm connectivity.

---

## 4. Running Test Suites & Linting

```bash
# Backend Test Suite (955 tests)
cd backend
pytest -q

# Frontend Test Suite (223 tests)
cd frontend
npm test -- --run

# Frontend Production Build Check
npm run build
```

---

## 5. Adding a New Agent or Tool

### 5.1 Creating a New Specialized Agent
1. Create agent logic in `backend/app/core/agents/your_agent.py` inheriting from `BaseAgent`.
2. Register the agent in `backend/app/core/platform/intelligence/engine.py`.
3. Add corresponding test suites in `backend/tests/unit/test_agent_your_agent.py`.

### 5.2 Registering a Custom MCP Tool
1. Register tool definition in `backend/app/services/mcp/` or via UI (`UserMcpMarket.jsx`).
2. Implement schema validation rules in Pydantic models.
3. Test tool invocation in `backend/tests/unit/test_mcp_*.py`.
