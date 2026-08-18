# AegisAI – Enterprise Autonomous Multi-Agent AI Platform

AegisAI is a multi-tenant, workspace-isolated autonomous agent operating system featuring real-time stream execution, security critic gates, vector memory databases, and MCP server integrations.

---

## 1. Setup Instructions

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables in `.env` (see section below).
5. Apply database migrations:
   ```bash
   alembic upgrade head
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Create `.env` configuration file:
   ```bash
   echo VITE_API_URL=http://localhost:8000 > .env
   ```

---

## 2. Environment Variables (.env)

Define the following parameters in `backend/.env`:
```ini
# System Environment
ENVIRONMENT=dev

# DB Persistence
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=aegisai
POSTGRES_PORT=5432

# Redis Cache
REDIS_HOST=localhost
REDIS_PORT=6379

# Provider Keys
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
ANTHROPIC_API_KEY=your_anthropic_key
TAVILY_API_KEY=your_tavily_key

# Memory Configurations
MEMORY_PROVIDER=postgres
RESEARCH_PROVIDER=tavily
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
```

---

## 3. Database & Cache Services

1. **PostgreSQL**: Stores users, permissions, workspace records, executions, events, checkpoints, and vector memories. Make sure the database is running and credentials match.
2. **Redis**: Manages rate-limiting counters, token session blacklists, execution locks, and streaming queues.

---

## 4. Running the Applications

### Start Backend Dev Server
From the `backend` folder:
```bash
python app/main.py
```
FastAPI runs on `http://localhost:8000`. API docs are available at `http://localhost:8000/docs`.

### Start Frontend Dev Server
From the `frontend` folder:
```bash
npm run dev
```
The client dashboard opens on `http://localhost:5173`.

---

## 5. Main Functional Flows

### Authentication
- Users register `/auth/register` (which auto-provisions a default workspace) and login `/auth/login`.
- JWT token is returned and saved locally. Requests include `Authorization: Bearer <token>`.
- Auto-token rotation intercepts `401` errors and refreshes using cookies `/auth/refresh`.

### AI Execution & SSE Streaming
- Prompt submissions send post streams: `POST /agent/execute/stream`.
- Graph execution events (`PLANNER_STARTED`, `RESEARCH_STARTED`, `TOOL_COMPLETED`, etc.) are read via async ReadableStream chunks to log stages real-time.

### Human Confirmation
- If an agent prompts a high-risk tool execution, it streams `WAITING_FOR_CONFIRMATION` alongside a secure token.
- Approvals trigger `POST /confirm` with the validation token.

### Cancellation
- Clicking Stop invokes `POST /cancel` which sets the cancellation signal key in Redis to cancel pipeline workflows instantly.

---

## 6. Document Processing Pipeline

AegisAI supports uploading and parsing various files into clean, normalized text in a secure background process:

- **Secure Storage**: Resolves files into localized `workspaces/<workspace_id>/documents/<doc_id>/original_file` paths.
- **Multiprocess Extractors**: Parsers for PDF, DOCX, PPTX, XLSX, TXT, CSV, Image, and Audio/Video containers.
- **Format Normalizer**: Standardizes whitespace, unicode control characters, and line endings.
- **Heuristic Scanner**: Scans for prompt injection triggers without editing valid payload text.
- **API Endpoints**:
  - `POST /api/v1/documents/upload` - Tenant-isolated file uploader.
  - `POST /api/v1/documents/{id}/process` - Queue background text extraction.
  - `GET /api/v1/documents/{id}/status` - Check current extraction state.

---

## 7. Testing

### Run Backend Tests
From the project root:
```bash
python -m pytest backend/tests
```

### Build Frontend
From the `frontend` folder:
```bash
npm run build
```
