from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.core.config import settings

# Setup SQLAlchemy connection pool
engine = create_engine(
    settings.get_database_url(),
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10
)

from app.database.base_class import Base

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
