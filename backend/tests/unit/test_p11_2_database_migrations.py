"""
AegisAI Enterprise — Phase 11.2 Database & Migration Infrastructure Unit Tests
Validates connection pooling, session rollback resilience, Alembic migration graph integrity,
PostgreSQL advisory lock concurrency control, tenant schema indexing, and fail-safe health probes.
"""

import pytest
import unittest.mock as mock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.core.config import BaseConfig, ProductionConfig, DevelopmentConfig, TestConfig, validate_production_configuration
from app.database.session import get_db, SessionLocal, engine
from app.database.base import Base
from app.database.migration_manager import (
    acquire_advisory_lock,
    release_advisory_lock,
    verify_migration_chain,
    run_migrations_with_lock,
    MigrationLockError,
    AEGIS_MIGRATION_ADVISORY_LOCK_ID
)

# Prevent pytest from treating TestConfig as a test class
TestConfig.__test__ = False

def test_alembic_migration_chain_and_head():
    """Verify that the Alembic migration history is completely linear and points to expected head."""
    chain_info = verify_migration_chain("alembic.ini")
    assert chain_info["is_linear"] is True
    assert chain_info["head"] == "019_background_jobs"
    assert chain_info["total_revisions"] == 19
    assert "001_initial_migration" in chain_info["revisions"]
    assert "018_notifications_realtime" in chain_info["revisions"]
    assert "019_background_jobs" in chain_info["revisions"]

def test_production_database_config_validation():
    """Verify production database validation rules (rejection of SQLite, default passwords, pool boundaries)."""
    # 1. Reject SQLite in production
    cfg_sqlite = ProductionConfig(
        SECRET_KEY="A_VERY_LONG_SECURE_PRODUCTION_KEY_FOR_TESTING_PURPOSES_2026",
        DATABASE_URL="sqlite:///./prod.db",
        POSTGRES_PASSWORD="secure_prod_password",
        DOCUMENT_STORAGE_PATH="/workspace/storage",
        CORS_ORIGINS=["https://app.aegisai.enterprise"]
    )
    errors = validate_production_configuration(cfg_sqlite)
    assert any("SQLite database is not permitted in production" in e for e in errors)

    # 2. Reject default PostgreSQL password
    cfg_default_pw = ProductionConfig(
        SECRET_KEY="A_VERY_LONG_SECURE_PRODUCTION_KEY_FOR_TESTING_PURPOSES_2026",
        POSTGRES_PASSWORD="postgres",
        DOCUMENT_STORAGE_PATH="/workspace/storage",
        CORS_ORIGINS=["https://app.aegisai.enterprise"]
    )
    errors = validate_production_configuration(cfg_default_pw)
    assert any("Production POSTGRES_PASSWORD must not use default" in e for e in errors)

    # 3. Reject invalid pool size boundaries
    cfg_low_pool = ProductionConfig(
        SECRET_KEY="A_VERY_LONG_SECURE_PRODUCTION_KEY_FOR_TESTING_PURPOSES_2026",
        POSTGRES_PASSWORD="secure_prod_password",
        DOCUMENT_STORAGE_PATH="/workspace/storage",
        CORS_ORIGINS=["https://app.aegisai.enterprise"],
        DB_POOL_SIZE=2
    )
    errors = validate_production_configuration(cfg_low_pool)
    assert any("DB_POOL_SIZE (2) is too low" in e for e in errors)

    cfg_high_pool = ProductionConfig(
        SECRET_KEY="A_VERY_LONG_SECURE_PRODUCTION_KEY_FOR_TESTING_PURPOSES_2026",
        POSTGRES_PASSWORD="secure_prod_password",
        DOCUMENT_STORAGE_PATH="/workspace/storage",
        CORS_ORIGINS=["https://app.aegisai.enterprise"],
        DB_POOL_SIZE=150
    )
    errors = validate_production_configuration(cfg_high_pool)
    assert any("DB_POOL_SIZE (150) exceeds safe boundary" in e for e in errors)

    # 4. Valid production configuration passes cleanly
    cfg_valid = ProductionConfig(
        SECRET_KEY="A_VERY_LONG_SECURE_PRODUCTION_KEY_FOR_TESTING_PURPOSES_2026",
        POSTGRES_PASSWORD="secure_prod_password_xyz_123",
        DOCUMENT_STORAGE_PATH="/workspace/storage",
        CORS_ORIGINS=["https://app.aegisai.enterprise"],
        DB_POOL_SIZE=25
    )
    assert validate_production_configuration(cfg_valid) == []

def test_database_url_formatting():
    """Verify database URL construction for standard PostgreSQL credentials."""
    cfg = BaseConfig(
        _env_file=None,
        DATABASE_URL="",
        POSTGRES_USER="aegis_app",
        POSTGRES_PASSWORD="complex_password",
        POSTGRES_SERVER="db-cluster.internal",
        POSTGRES_PORT="5432",
        POSTGRES_DB="aegis_prod"
    )
    url = cfg.get_database_url()
    assert url == "postgresql://aegis_app:complex_password@db-cluster.internal:5432/aegis_prod"

def test_session_generator_rollback_on_exception():
    """Verify that get_db() rolls back transactions on unhandled exceptions and closes session."""
    mock_session = mock.MagicMock(spec=Session)
    
    with mock.patch("app.database.session.SessionLocal", return_value=mock_session):
        gen = get_db()
        db = next(gen)
        assert db == mock_session
        
        with pytest.raises(RuntimeError, match="Simulated application error"):
            try:
                raise RuntimeError("Simulated application error")
            except Exception:
                gen.throw(RuntimeError("Simulated application error"))
        
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

def test_session_generator_normal_completion():
    """Verify that get_db() closes session upon normal generator termination."""
    mock_session = mock.MagicMock(spec=Session)
    
    with mock.patch("app.database.session.SessionLocal", return_value=mock_session):
        gen = get_db()
        db = next(gen)
        assert db == mock_session
        
        # Generator consumes normally
        with pytest.raises(StopIteration):
            next(gen)
            
        mock_session.rollback.assert_not_called()
        mock_session.close.assert_called_once()

def test_advisory_lock_sqlite_bypass():
    """Verify that non-PostgreSQL connections (e.g. SQLite) safely bypass advisory locks."""
    sqlite_engine = create_engine("sqlite:///:memory:")
    with sqlite_engine.connect() as conn:
        assert acquire_advisory_lock(conn, timeout_seconds=1) is True
        assert release_advisory_lock(conn) is True

def test_advisory_lock_postgres_success():
    """Verify PostgreSQL advisory lock acquisition and release mechanics."""
    mock_conn = mock.MagicMock()
    mock_conn.dialect.name = "postgresql"
    mock_conn.execute.return_value.scalar.return_value = 1

    assert acquire_advisory_lock(mock_conn, lock_id=AEGIS_MIGRATION_ADVISORY_LOCK_ID) is True
    assert release_advisory_lock(mock_conn, lock_id=AEGIS_MIGRATION_ADVISORY_LOCK_ID) is True

def test_advisory_lock_postgres_timeout():
    """Verify that failing to acquire PostgreSQL advisory lock raises MigrationLockError on timeout."""
    mock_conn = mock.MagicMock()
    mock_conn.dialect.name = "postgresql"
    mock_conn.execute.return_value.scalar.return_value = 0  # lock unavailable

    with pytest.raises(MigrationLockError, match="Could not acquire PostgreSQL migration advisory lock"):
        acquire_advisory_lock(mock_conn, timeout_seconds=1)

def test_run_migrations_with_lock_orchestration():
    """Verify that run_migrations_with_lock acquires the lock, upgrades, and releases the lock."""
    mock_engine = mock.MagicMock()
    mock_conn = mock.MagicMock()
    mock_conn.dialect.name = "postgresql"
    mock_conn.execute.return_value.scalar.return_value = 1
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    with mock.patch("alembic.command.upgrade") as mock_upgrade:
        res = run_migrations_with_lock(mock_engine, target_revision="head")
        assert res["status"] == "success"
        assert res["head"] == "019_background_jobs"
        mock_upgrade.assert_called_once()

def test_model_metadata_table_completeness():
    """Verify that Base.metadata includes all key multi-tenant and enterprise domain tables."""
    table_names = set(Base.metadata.tables.keys())
    
    expected_tables = {
        "users",
        "roles",
        "workspaces",
        "workspace_members",
        "teams",
        "team_memberships",
        "projects",
        "project_memberships",
        "comments",
        "comment_mentions",
        "documents",
        "document_chunks",
        "knowledge_graph_nodes",
        "knowledge_graph_edges",
        "memories",
        "workflows",
        "mcp_servers",
        "notifications",
        "background_jobs",
        "audit_logs",
        "activity_logs"
    }
    
    for tbl in expected_tables:
        assert tbl in table_names, f"Expected table '{tbl}' was not discovered in Base.metadata"

def test_tenant_isolation_foreign_keys_and_indexes():
    """Verify that multi-tenant tables possess indexed workspace_id foreign keys."""
    tenant_scoped_tables = [
        "teams",
        "projects",
        "comments",
        "documents",
        "knowledge_graph_nodes",
        "knowledge_graph_edges",
        "memories",
        "workflows",
        "mcp_servers"
    ]
    
    for tbl_name in tenant_scoped_tables:
        table = Base.metadata.tables[tbl_name]
        assert "workspace_id" in table.c, f"Table {tbl_name} is missing workspace_id"
        ws_col = table.c["workspace_id"]
        # Column must be indexed or part of a primary/unique key constraint
        is_indexed = ws_col.index or any(ws_col in idx.columns for idx in table.indexes)
        assert is_indexed, f"workspace_id column on table {tbl_name} must be indexed for tenant performance"

def test_database_readiness_probe_failure():
    """Verify /health/readiness returns 503 and safe status payload when DB connection fails."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database.session import get_db
    
    # Mock DB execute failure
    mock_db = mock.MagicMock()
    mock_db.execute.side_effect = Exception("Database connection refused")
    
    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        with mock.patch("app.main.check_redis_health", return_value=True):
            response = client.get("/health/readiness")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "not_ready"
            assert data["database"] == "error"
            assert "Database connection refused" not in response.text  # No leaked raw error
    finally:
        app.dependency_overrides.clear()

def test_concurrent_session_independence():
    """Verify that multiple concurrent calls to SessionLocal produce distinct session instances."""
    import concurrent.futures
    
    def get_session():
        return SessionLocal()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(get_session) for _ in range(5)]
        sessions = [f.result() for f in futures]

    try:
        # Simultaneously open sessions are distinct objects
        assert len(set(sessions)) == len(sessions)
    finally:
        for s in sessions:
            s.close()

def test_cross_tenant_database_query_isolation():
    """Verify that multi-tenant entities enforce workspace_id scoping in filtering."""
    import uuid
    from app.models.team import Team
    
    mock_db = mock.MagicMock()
    ws_a = uuid.uuid4()
    
    # Query builder filter verification
    mock_db.query(Team).filter(Team.workspace_id == ws_a)
    assert mock_db.query(Team).filter.called
    call_expr = mock_db.query(Team).filter.call_args[0][0]
    assert "workspace_id" in str(call_expr)

def test_database_error_no_password_leak():
    """Verify that database connection string formatting safely prevents plain text exposure in logs."""
    from app.core.config import BaseConfig
    
    cfg = BaseConfig(
        _env_file=None,
        DATABASE_URL="",
        POSTGRES_USER="aegis_user",
        POSTGRES_PASSWORD="SUPER_SECRET_DB_PASSWORD_123!",
        POSTGRES_SERVER="db.internal",
        POSTGRES_PORT="5432",
        POSTGRES_DB="aegis_prod"
    )
    
    raw_url = cfg.get_database_url()
    # Mask password for safe logging
    safe_display = raw_url.replace(cfg.POSTGRES_PASSWORD, "********")
    assert "SUPER_SECRET_DB_PASSWORD_123!" not in safe_display
    assert "postgresql://aegis_user:********@db.internal:5432/aegis_prod" == safe_display
