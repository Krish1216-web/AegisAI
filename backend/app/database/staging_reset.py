"""
AegisAI Enterprise — Safe Staging Database Reset Utility

Strict Safety Controls:
1. Environment Gating: CANNOT run against production ('prod') or any non-staging environment.
2. Confirmation Required: Refuses execution without explicit confirmation flag (--confirm-staging-reset or force=True).
3. Advisory Lock: Acquires PostgreSQL advisory lock during reset sequence to prevent race conditions.
4. Schema Migration: Re-executes Alembic migrations from clean head.
5. Deterministic Seeding: Seeds controlled staging test entities via staging_seed.
"""

import os
import sys
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.database.session import SessionLocal, engine
from app.database.migration_manager import run_migrations_with_lock
from app.database.staging_seed import seed_staging_environment


class StagingResetSafetyError(Exception):
    """Raised when safety prerequisites for staging reset are violated."""
    pass


def reset_staging_database(force: bool = False) -> dict:
    """
    Safely resets the staging database and seeds deterministic test fixtures.
    Fails immediately if invoked in non-staging environments or without explicit force confirmation.
    """
    env = os.getenv("ENVIRONMENT", settings.ENVIRONMENT).lower()
    
    # 1. Strict Environment Guard
    if env not in ["staging", "stage"]:
        err_msg = (
            f"CRITICAL SAFETY VIOLATION: Staging database reset attempted in '{env}' environment! "
            "Reset operations are strictly forbidden on production or non-staging environments."
        )
        logger.critical(err_msg)
        raise StagingResetSafetyError(err_msg)

    # 2. Explicit Confirmation Guard
    if not force:
        err_msg = (
            "SAFETY GUARD: Staging reset requires explicit confirmation (force=True or --confirm-staging-reset). "
            "Aborting reset to prevent accidental data loss."
        )
        logger.warning(err_msg)
        raise StagingResetSafetyError(err_msg)

    logger.warning("Initiating authorized staging database reset sequence under advisory lock...")

    db: Session = SessionLocal()
    try:
        # 3. Clean and reset staging tables
        # Drop all tables in public schema cleanly (or recreate schema)
        with engine.connect() as conn:
            with conn.begin():
                # Advisory lock for reset operation
                conn.execute(text("SELECT pg_advisory_xact_lock(987654321)"))
                conn.execute(text("DROP SCHEMA public CASCADE;"))
                conn.execute(text("CREATE SCHEMA public;"))
                conn.execute(text("GRANT ALL ON SCHEMA public TO CURRENT_USER;"))
                conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        logger.info("Staging public schema recreated cleanly.")

        # 4. Re-run Alembic migrations with lock
        logger.info("Applying full migration chain on clean staging schema...")
        mig_ok = run_migrations_with_lock()
        if not mig_ok:
            raise RuntimeError("Alembic migration failed during staging database reset sequence!")

        # 5. Re-seed deterministic staging fixtures
        logger.info("Seeding deterministic staging fixtures...")
        seed_summary = seed_staging_environment(db)
        logger.info(f"Staging database reset and seed completed: {seed_summary}")

        return {
            "status": "success",
            "environment": "staging",
            "migrations": "current_head",
            "seed_summary": seed_summary
        }
    finally:
        db.close()


if __name__ == "__main__":
    if "--confirm-staging-reset" in sys.argv:
        try:
            result = reset_staging_database(force=True)
            print(f"Staging database reset successful: {result}")
            sys.exit(0)
        except Exception as e:
            print(f"Staging reset failed: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(
            "ERROR: Staging database reset requires the '--confirm-staging-reset' CLI flag.\n"
            "Usage: python -m app.database.staging_reset --confirm-staging-reset",
            file=sys.stderr
        )
        sys.exit(1)
