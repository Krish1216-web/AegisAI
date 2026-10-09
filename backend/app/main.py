from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from loguru import logger
import time

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import register_exception_handlers, AegisBaseException
from app.database.session import get_db
from app.database.redis import check_redis_health
from app.api.v1.router import api_router

# Initialize structured logging system
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

from app.core.security_headers import SecurityHeadersMiddleware
from app.core.request_limits import RequestSizeLimitMiddleware
from app.core.correlation import CorrelationMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

# 1. Register security TrustedHostMiddleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=settings.ALLOWED_HOSTS
)

# 2. Register Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# 3. Register Request Size Limit Middleware
app.add_middleware(RequestSizeLimitMiddleware)

# 4. Register Request Correlation & Telemetry Middleware
app.add_middleware(CorrelationMiddleware)

# 5. Register Explicit CORS policy middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 3. Register custom unified exception handlers
register_exception_handlers(app)

# 4. Mount versioned API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# 5. OpenAPI & Documentation compatibility routes
@app.get(f"{settings.API_V1_STR}/openapi.json", include_in_schema=False)
def openapi_v1_alias():
    """
    OpenAPI schema compatibility endpoint mounted under versioned prefix.
    """
    return JSONResponse(app.openapi())

@app.get(f"{settings.API_V1_STR}/docs", include_in_schema=False)
def docs_v1_redirect():
    """Redirect /api/v1/docs to /docs."""
    return RedirectResponse(url="/docs")

@app.get(f"{settings.API_V1_STR}/redoc", include_in_schema=False)
def redoc_v1_redirect():
    """Redirect /api/v1/redoc to /redoc."""
    return RedirectResponse(url="/redoc")

# Initialize startup application state
app.state.seed_status = "uninitialized"
app.state.seed_error = None

from app.core.config import validate_production_configuration

@app.on_event("startup")
async def startup_event():
    logger.info("AegisAI backend startup sequence initiated.")
    
    # Fail-fast production configuration validation
    cfg_errors = validate_production_configuration(settings)
    if cfg_errors:
        for err in cfg_errors:
            logger.critical(f"CONFIGURATION ERROR: {err}")
        raise RuntimeError(f"AegisAI production startup aborted due to configuration errors: {'; '.join(cfg_errors)}")
        
    try:
        from app.database.session import SessionLocal
        from app.database.seed import seed_database
        db = SessionLocal()
        try:
            seed_database(db)
            app.state.seed_status = "completed"
            app.state.seed_error = None
            logger.info("Database auto-seeding completed successfully.")
        finally:
            db.close()
    except Exception as e:
        app.state.seed_status = "failed"
        app.state.seed_error = str(e)
        logger.error(f"Database seeding failed during startup initialization: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("AegisAI backend shutdown sequence initiated.")

@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Diagnostic health check endpoint executing active pings to PostgreSQL and Redis.
    """
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}")

    redis_ok = check_redis_health()

    overall_status = "ONLINE" if (db_ok and redis_ok) else "DEGRADED"

    return {
        "status": overall_status,
        "timestamp": time.time(),
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "dependencies": {
            "database": "CONNECTED" if db_ok else "DISCONNECTED",
            "redis": "CONNECTED" if redis_ok else "DISCONNECTED"
        },
        "seed_status": getattr(app.state, "seed_status", "unknown")
    }

@app.get("/health/liveness", tags=["Health"])
def liveness_probe():
    """
    Kubernetes / Container Liveness Probe.
    Returns 200 OK immediately if the ASGI event loop is running.
    """
    return {
        "status": "alive",
        "timestamp": time.time(),
        "service": settings.PROJECT_NAME
    }

@app.get("/health/readiness", tags=["Health"])
def readiness_probe(db: Session = Depends(get_db)):
    """
    Kubernetes / Container Readiness Probe.
    Returns 200 OK if critical backend dependencies (DB, Redis) are healthy and ready to serve requests.
    """
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.error(f"Readiness check - DB failed: {e}")

    redis_ok = check_redis_health()
    is_ready = db_ok and redis_ok

    if not is_ready:
        from fastapi import Response
        return Response(
            content='{"status": "not_ready", "database": "%s", "redis": "%s"}' % (
                "ok" if db_ok else "error",
                "ok" if redis_ok else "error"
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )

    return {
        "status": "ready",
        "timestamp": time.time(),
        "database": "ok",
        "redis": "ok"
    }

@app.get("/health/dependencies", tags=["Health"])
def dependencies_health_probe(db: Session = Depends(get_db)):
    """
    Comprehensive dependency health evaluation for PostgreSQL, Redis, Queues, Workers, and Storage.
    """
    import os
    from app.core.queue import QueueManager
    from app.core.metrics import metrics_registry

    db_status = "healthy"
    db_latency_ms = None
    try:
        t0 = time.perf_counter()
        db.execute(text("SELECT 1"))
        db_latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        metrics_registry.record_db_query(duration_ms=db_latency_ms)
    except Exception as e:
        logger.error(f"PostgreSQL dependency check error: {e}")
        db_status = "unhealthy"
        metrics_registry.record_db_query(duration_ms=0, is_failure=True)

    redis_ok = check_redis_health()
    redis_status = "healthy" if redis_ok else "unhealthy"

    queue_mgr = QueueManager()
    active_workers = queue_mgr.get_active_workers()
    queue_depths = queue_mgr.get_queue_depth()

    storage_path = getattr(settings, "DOCUMENT_STORAGE_PATH", "storage")
    storage_accessible = os.path.isdir(storage_path) or os.path.exists(storage_path)

    overall = "healthy"
    if db_status != "healthy" or redis_status != "healthy":
        overall = "unhealthy"
    elif not storage_accessible:
        overall = "degraded"

    return {
        "status": overall,
        "timestamp": time.time(),
        "environment": settings.ENVIRONMENT,
        "dependencies": {
            "database": {
                "status": db_status,
                "latency_ms": db_latency_ms
            },
            "redis": {
                "status": redis_status
            },
            "worker_cluster": {
                "active_workers_count": len(active_workers),
                "queue_depths": queue_depths
            },
            "storage": {
                "status": "accessible" if storage_accessible else "inaccessible",
                "path": storage_path
            }
        }
    }

@app.get("/version", tags=["Version"])
@app.get(f"{settings.API_V1_STR}/version", tags=["Version"])
def version_info():
    """
    Application build metadata and runtime version endpoint.
    Exposes immutable version identifiers and build information safely without leaking secrets.
    """
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "git_commit": settings.GIT_COMMIT_SHA,
        "environment": settings.ENVIRONMENT,
        "build_timestamp": settings.BUILD_TIMESTAMP if settings.BUILD_TIMESTAMP else None,
        "api_version": "v1"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
