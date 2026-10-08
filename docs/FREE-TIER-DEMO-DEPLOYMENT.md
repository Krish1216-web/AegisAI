# AegisAI — Free Public Demo Deployment Guide

> **Release Version**: `v1.0.0-rc.1`  
> **Target Architecture**: Vercel (Frontend) + Render (Backend) + Supabase (PostgreSQL) + Upstash (Redis)  
> **Environment Classification**: Public Demo / Evaluation Tier (Zero Cloud Cost)

---

## 🧭 Overview & Topology

This runbook guides you through deploying a live, publicly accessible demonstration of **AegisAI v1.0.0-rc.1** using 100% free-tier managed cloud services.

```mermaid
flowchart TD
    subgraph Client ["Client Layer"]
        Browser["User Browser / Evaluator"]
    end

    subgraph Vercel ["Frontend (Vercel)"]
        SPA["React 19 SPA (Vite + Tailwind CSS 4)"]
        VercelRouting["vercel.json SPA Deep-Link Rewrites"]
    end

    subgraph Render ["Backend API (Render)"]
        FastAPI["FastAPI ASGI Web Service"]
        Alembic["Alembic Migrations (001 -> 019)"]
        MemoryCore["In-Memory Showcase Engine & RBAC"]
    end

    subgraph ManagedDB ["Managed Cloud Data Stores"]
        Supabase[("Supabase PostgreSQL (ap-south-1)\nSession Pooler :5432")]
        Upstash[("Upstash Serverless Redis\nTLS rediss://")]
    end

    Browser -->|HTTPS| SPA
    SPA -->|REST / SSE with JWT| FastAPI
    FastAPI -->|psycopg2 / SQLAlchemy| Supabase
    FastAPI -->|redis-py TLS Pool| Upstash
```

---

## ⚠️ Free-Tier Operational Boundaries & Constraints

To maintain 100% free hosting, the public demo environment operates under the following known boundaries:

| Dimension | Production Target | Free Public Demo Deployment |
| :--- | :--- | :--- |
| **Compute Continuity** | High Availability Multi-Replica | Render Free Tier spins down after 15 minutes of inactivity (cold start takes ~30–50s). |
| **Document Storage** | AWS S3 / MinIO Object Storage | Render filesystem is ephemeral; uploaded documents reset on container restart. |
| **Database Pool** | Dedicated RDS / PostgreSQL (100 conn) | Supabase Free Session Pooler (port `5432`, `DB_POOL_SIZE=5`). |
| **Redis Quota** | Dedicated Redis Cluster | Upstash Free Tier (10,000 commands/day). |
| **Showcase Mode** | Real Multi-LLM API Keys | In-memory Showcase Mode (`/showcase`) runs zero-cost deterministic demonstrations. |

---

## 📋 Prerequisites Checklist

Before beginning deployment, ensure you have active accounts on:
1. [GitHub](https://github.com) (Repository hosting)
2. [Supabase](https://supabase.com) (Managed PostgreSQL)
3. [Upstash](https://upstash.com) (Serverless Redis)
4. [Render](https://render.com) (FastAPI Web Service)
5. [Vercel](https://vercel.com) (React SPA Hosting)

---

## 🛠️ Step-by-Step Deployment Instructions

### Step 1: Supabase PostgreSQL Configuration

1. Log in to [Supabase](https://supabase.com) and create a project in your preferred region (e.g., `ap-south-1`).
2. Navigate to **Project Settings $\to$ Database $\to$ Connection String**.
3. Select **URI** and choose **Session Mode (Port 5432)** or **Shared Pooler**.
4. The connection string format:
   ```text
   postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
   ```
5. *(Note: AegisAI backend automatically normalizes `postgres://` prefixes to `postgresql://` and sets appropriate connection pre-ping options).*

---

### Step 2: Upstash Redis Configuration

1. Log in to [Upstash](https://upstash.com) and click **Create Database**.
2. Name your database (e.g. `aegisai-redis`) and select your region (e.g., `ap-south-1`).
3. Under **Connect to your database**, copy the **`rediss://`** connection URL:
   ```text
   rediss://default:[YOUR-PASSWORD]@[YOUR-ENDPOINT].upstash.io:6379
   ```

---

### Step 3: Render Backend Deployment

1. Log in to [Render](https://render.com) and click **New $\to$ Web Service**.
2. Connect your GitHub repository (`AegisAI`) and branch (`phase-11-deployment`).
3. Configure the service settings:
   - **Name**: `aegisai-backend`
   - **Region**: Same as Supabase/Upstash (e.g., Singapore / Mumbai)
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
   - **Health Check Path**: `/health/liveness`
4. Add the following **Environment Variables** in the Render Dashboard:

| Key | Value | Description |
| :--- | :--- | :--- |
| `PYTHON_VERSION` | `3.12.8` | Pins canonical Python 3.12 runtime for `psycopg2-binary` compatibility |
| `ENVIRONMENT` | `prod` | Activates production security controls and invariants |
| `APP_VERSION` | `1.0.0-rc.1` | Release candidate version tag |
| `SECRET_KEY` | *(Generate 32+ char key)* | JWT signing secret |
| `DATABASE_URL` | `postgresql://...` | Supabase Session Pooler connection URL |
| `REDIS_URL` | `rediss://...` | Upstash TLS Redis connection URL |
| `CORS_ORIGINS` | `https://your-frontend.vercel.app,http://localhost:5173` | Allowed frontend origins |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,*.onrender.com,*.vercel.app` | Trusted host patterns |
| `DB_POOL_SIZE` | `5` | Free-tier database connection pool boundary |
| `DB_MAX_OVERFLOW` | `2` | Connection pool overflow limit |
| `MEMORY_PROVIDER` | `mock` | Deterministic memory provider for demo |
| `RESEARCH_PROVIDER` | `mock` | Mock research search provider |

> **Runtime & Driver Architecture Note**:
> AegisAI uses synchronous SQLAlchemy backed by **`psycopg2-binary>=2.9.9`** running on **Python 3.12 (3.12.8)**. Render automatically picks up `.python-version` / `runtime.txt` (pinning `3.12.8`), ensuring precompiled wheels install cleanly without C-extension compilation failures. Both Alembic migrations (`alembic/env.py`) and runtime database sessions (`app/database/session.py`) share the same canonical URL normalizer (`normalize_database_url()`), which deterministically converts all PostgreSQL connection variants (`postgres://`, `postgresql://`, `postgresql+psycopg://`, `postgresql+psycopg3://`, `postgresql+psycopg2://`) to canonical `postgresql+psycopg2://`, guaranteeing SQLAlchemy explicitly resolves to the `psycopg2` driver.

5. Click **Create Web Service**. Render will automatically build the container, execute database migrations from `001` to `019_background_jobs`, auto-seed default roles and demo users, and start FastAPI.

---

### Step 4: Vercel Frontend Deployment

1. Log in to [Vercel](https://vercel.com) and click **Add New $\to$ Project**.
2. Select your GitHub repository (`AegisAI`).
3. In the project setup modal:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend` *(Click Edit and choose `frontend`)*
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Expand **Environment Variables** and add:
   - `VITE_API_URL`: `https://aegisai-backend.onrender.com` *(Use your Render backend URL)*
5. Click **Deploy**.
6. Vercel will build the React 19 bundle and deploy the SPA with `frontend/vercel.json` rewrites enabled.

---

## 🔍 Verification & Smoke Test Matrix

Once deployment is complete, verify the live services using this checklist:

### 1. Backend Diagnostics
Open in browser or terminal:
```bash
# 1. Check ASGI Liveness
curl -s https://your-backend.onrender.com/health/liveness
# Expected: {"status":"alive","timestamp":...,"service":"AegisAI Enterprise Backend"}

# 2. Check Database & Redis Connectivity
curl -s https://your-backend.onrender.com/health
# Expected: {"status":"ONLINE","dependencies":{"database":"CONNECTED","redis":"CONNECTED"}}

# 3. Check API Documentation
# Visit: https://your-backend.onrender.com/docs
```

### 2. Frontend Interface & Showcase
1. Open your Vercel URL: `https://your-frontend.vercel.app`.
2. Verify that the login page loads with the Enterprise Design System.
3. Test **Showcase Mode**:
   - Navigate to `https://your-frontend.vercel.app/showcase`
   - Run the 5-step guided demonstration walkthrough:
     - 1. Intelligence Query
     - 2. DAG Decomposition
     - 3. Agent Execution
     - 4. Evidence & Citation Verification
     - 5. SHA-256 Audit Chain Verification
4. Test **Authenticated Workspaces**:
   - Log in with seeded demo user: `user@aegis.ai` / `user2026`
   - Or admin user: `admin@aegis.ai` / `admin2026`
   - Verify access to AI OS Workspace, Agent Center, Memory Vault, MCP Center, Knowledge Graph, and Automation Studio.

---

## 🔄 Local vs Cloud Deployment Parity

| Environment | Database | Cache/Queue | Vector Store | Auth |
| :--- | :--- | :--- | :--- | :--- |
| **Local Dev** | SQLite (`sqlite:///./aegisai.db`) | Localhost Redis (`:6379`) | Local Qdrant / Mock | Local JWT |
| **Free Demo** | Supabase PG (Session Pooler) | Upstash Serverless (`rediss://`) | Mock Embeddings / PG | Cloud JWT |
| **Production** | Dedicated PostgreSQL Cluster | HA Redis Cluster | Dedicated Qdrant Node | Enterprise SSO/OIDC |

---

## 🆘 Troubleshooting Common Issues

### Issue 1: Render Cold Start Timeout (502 / 504)
- **Cause**: Render free tier instances go to sleep after 15 minutes of inactivity.
- **Remedy**: The first request may take 30–50 seconds to wake up the container. Subsequent requests respond in sub-100ms.

### Issue 2: Vercel Deep-Link 404s on Refresh
- **Cause**: Client-side router deep link (e.g. `/showcase`) requested directly from CDN.
- **Remedy**: Ensure `frontend/vercel.json` contains `{"rewrites": [{"source": "/(.*)", "destination": "/index.html"}]}`. This has been committed to the repository.

### Issue 3: Supabase `remaining connection slots are reserved`
- **Cause**: Exceeding free-tier direct PostgreSQL connection limit.
- **Remedy**: Use the **Session Pooler** URL on port `5432` (`aws-0-ap-south-1.pooler.supabase.com:5432`) and keep `DB_POOL_SIZE=5` and `DB_MAX_OVERFLOW=2`.

### Issue 4: CORS Errors on API Requests
- **Cause**: Backend `CORS_ORIGINS` does not match the exact Vercel URL.
- **Remedy**: Add your custom Vercel domain to Render's `CORS_ORIGINS` environment variable (e.g., `https://your-project.vercel.app`).
