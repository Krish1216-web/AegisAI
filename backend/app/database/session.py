from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.core.config import settings

db_url = settings.get_database_url()

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    engine = create_engine(
        db_url,
        connect_args=connect_args
    )
else:
    # PostgreSQL connection options
    connect_args["connect_timeout"] = getattr(settings, "DB_CONNECT_TIMEOUT", 10)
    engine = create_engine(
        db_url,
        pool_pre_ping=getattr(settings, "DB_POOL_PRE_PING", True),
        pool_size=getattr(settings, "DB_POOL_SIZE", 20),
        max_overflow=getattr(settings, "DB_MAX_OVERFLOW", 10),
        pool_timeout=getattr(settings, "DB_POOL_TIMEOUT", 30),
        pool_recycle=getattr(settings, "DB_POOL_RECYCLE", 1800),
        connect_args=connect_args
    )

from app.database.base_class import Base

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """
    Yields a transactional database session per request.
    Automatically rolls back uncommitted transactions on unhandled exceptions
    and ensures the connection is safely returned to the pool.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
