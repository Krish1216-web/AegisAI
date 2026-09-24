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
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

from app.core.security_headers import SecurityHeadersMiddleware
from app.core.request_limits import RequestSizeLimitMiddleware

# 1. Register security TrustedHostMiddleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=settings.ALLOWED_HOSTS
)

# 2. Register Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# 3. Register Request Size Limit Middleware
app.add_middleware(RequestSizeLimitMiddleware)

# 4. Register Explicit CORS policy middleware
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

@app.on_event("startup")
async def startup_event():
    logger.info("AegisAI backend startup sequence initiated.")
    try:
        from app.database.session import SessionLocal
        from app.database.seed import seed_database
        db = SessionLocal()
        try:
            seed_database(db)
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Database seed skipped during startup: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("AegisAI backend shutdown sequence initiated.")

@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Diagnostic health check endpoint executing active pings to PostgreSQL and Redis.
    """
    # Check PostgreSQL connection health
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}")

    # Check Redis connection health
    redis_ok = check_redis_health()

    overall_status = "ONLINE" if (db_ok and redis_ok) else "DEGRADED"
    status_code = status.HTTP_200_OK if overall_status == "ONLINE" else status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": overall_status,
        "timestamp": time.time(),
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "dependencies": {
            "database": "CONNECTED" if db_ok else "DISCONNECTED",
            "redis": "CONNECTED" if redis_ok else "DISCONNECTED"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
