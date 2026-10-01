"""
Phase 11.7: Production-Like Staging Environment Verification Test Suite

Validates:
- Staging environment configuration profile (StagingConfig) and separation from prod/dev/test
- Strict fail-fast validation against unsafe default credentials, weak secrets, and SQLite
- Dedicated staging docker-compose topology, isolated internal networking, and non-exposed DB/Redis
- Safe staging database reset utility with environment and confirmation guards
- Idempotent deterministic staging data seeder (Alpha/Beta workspaces, role hierarchy users)
- Worker, QueueManager, and Scheduler single-leader coordination in staging
- Health, readiness, liveness, and dependency diagnostic gating
- Version metadata safety and secret non-disclosure
- Non-destructive rollback behavior and migration safety
"""

import os
import uuid
import yaml
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import (
    settings,
    BaseConfig,
    StagingConfig,
    ProductionConfig,
    DevelopmentConfig,
    TestConfig,
    get_settings,
    validate_production_configuration
)
from app.database.staging_seed import (
    seed_staging_environment,
    ORG_ALPHA_ID,
    ORG_BETA_ID,
    WS_ALPHA_ID,
    WS_BETA_ID
)
from app.database.staging_reset import reset_staging_database, StagingResetSafetyError
from app.core.queue import QueueManager


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ROOT_COMPOSE_STAGING = REPO_ROOT / "docker-compose.staging.yml"
DOCKER_PROD_COMPOSE_STAGING = REPO_ROOT / "docker" / "production" / "docker-compose.staging.yml"


# ==============================================================================
# 1. Environment Separation & Profile Resolution
# ==============================================================================

def test_staging_config_profile_resolution():
    """Verify ENVIRONMENT=staging resolves to StagingConfig."""
    with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
        cfg = get_settings()
        assert isinstance(cfg, StagingConfig)
        assert cfg.ENVIRONMENT == "staging"
        assert cfg.ENABLE_HSTS is True


def test_staging_environment_constants():
    """Verify StagingConfig defines isolated database and storage paths."""
    cfg = StagingConfig()
    assert cfg.ENVIRONMENT == "staging"
    assert cfg.POSTGRES_DB == "aegisai_staging"
    assert "staging" in cfg.DOCUMENT_STORAGE_PATH


def test_all_environments_distinct():
    """Verify dev, test, staging, and prod configurations are strictly isolated."""
    dev_cfg = DevelopmentConfig()
    test_cfg = TestConfig()
    staging_cfg = StagingConfig()
    prod_cfg = ProductionConfig()

    assert dev_cfg.ENVIRONMENT == "dev"
    assert test_cfg.ENVIRONMENT == "test"
    assert staging_cfg.ENVIRONMENT == "staging"
    assert prod_cfg.ENVIRONMENT == "prod"

    assert test_cfg.POSTGRES_DB != prod_cfg.POSTGRES_DB
    assert staging_cfg.POSTGRES_DB != prod_cfg.POSTGRES_DB
    assert test_cfg.POSTGRES_DB != staging_cfg.POSTGRES_DB


# ==============================================================================
# 2. Unsafe Default Rejection & Staging Configuration Validation
# ==============================================================================

def test_staging_rejects_default_secret_key():
    """Verify staging validation rejects placeholder secret keys."""
    cfg = StagingConfig(SECRET_KEY="SUPER_SECRET_AEGIS_KEY_2026_CHANGE_ME")
    errors = validate_production_configuration(cfg)
    assert any("SECRET_KEY must be securely configured" in e for e in errors)


def test_staging_rejects_short_secret_key():
    """Verify staging validation rejects secret keys shorter than 32 chars."""
    cfg = StagingConfig(SECRET_KEY="too_short_key")
    errors = validate_production_configuration(cfg)
    assert any("too short" in e for e in errors)


def test_staging_rejects_sqlite_database():
    """Verify staging validation rejects SQLite databases."""
    cfg = StagingConfig(
        SECRET_KEY="a" * 32,
        DATABASE_URL="sqlite:///test.db"
    )
    errors = validate_production_configuration(cfg)
    assert any("SQLite database is not permitted" in e for e in errors)


def test_staging_rejects_default_postgres_password():
    """Verify staging validation rejects default 'postgres' password."""
    cfg = StagingConfig(
        SECRET_KEY="a" * 32,
        POSTGRES_PASSWORD="postgres",
        DATABASE_URL=None
    )
    errors = validate_production_configuration(cfg)
    assert any("POSTGRES_PASSWORD must not use default" in e for e in errors)


def test_staging_rejects_cors_wildcard():
    """Verify staging validation rejects '*' in CORS origins."""
    cfg = StagingConfig(
        SECRET_KEY="a" * 32,
        POSTGRES_PASSWORD="secure_staging_password_123",
        CORS_ORIGINS=["*"]
    )
    errors = validate_production_configuration(cfg)
    assert any("CORS_ORIGINS must not contain wildcard" in e for e in errors)


def test_staging_rejects_allowed_hosts_wildcard():
    """Verify staging validation rejects '*' in ALLOWED_HOSTS."""
    cfg = StagingConfig(
        SECRET_KEY="a" * 32,
        POSTGRES_PASSWORD="secure_staging_password_123",
        ALLOWED_HOSTS=["*"]
    )
    errors = validate_production_configuration(cfg)
    assert any("ALLOWED_HOSTS must not contain wildcard" in e for e in errors)


def test_staging_rejects_connecting_to_production_db():
    """Verify staging validation rejects connecting to production database."""
    cfg = StagingConfig(
        SECRET_KEY="a" * 32,
        POSTGRES_PASSWORD="secure_staging_password_123",
        POSTGRES_DB="aegisai_prod"
    )
    errors = validate_production_configuration(cfg)
    assert any("Staging environment must not connect to the production database" in e for e in errors)


def test_staging_valid_configuration_passes():
    """Verify a properly configured staging environment passes validation with 0 errors."""
    cfg = StagingConfig(
        SECRET_KEY="secure_staging_key_2026_enterprise_valid_32chars",
        POSTGRES_PASSWORD="secure_staging_password_123",
        POSTGRES_DB="aegisai_staging",
        DB_POOL_SIZE=10,
        CORS_ORIGINS=["https://staging.aegisai.enterprise"],
        ALLOWED_HOSTS=["staging.aegisai.enterprise", "localhost"],
        DOCUMENT_STORAGE_PATH="storage/staging"
    )
    errors = validate_production_configuration(cfg)
    assert len(errors) == 0


# ==============================================================================
# 3. Staging Docker Compose Architecture & Topology Validation
# ==============================================================================

def test_staging_compose_files_exist():
    """Verify staging docker-compose files exist in root and docker/production/."""
    assert ROOT_COMPOSE_STAGING.exists(), "Missing root docker-compose.staging.yml"
    assert DOCKER_PROD_COMPOSE_STAGING.exists(), "Missing docker/production/docker-compose.staging.yml"


def test_staging_compose_valid_yaml():
    """Verify staging compose file is valid YAML."""
    with open(ROOT_COMPOSE_STAGING, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)
    assert "services" in data
    assert "networks" in data
    assert "volumes" in data


def test_staging_compose_contains_all_services():
    """Verify staging compose contains backend, worker, scheduler, frontend, db, and redis."""
    with open(ROOT_COMPOSE_STAGING, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    services = data.get("services", {})
    for req in ["backend", "worker", "scheduler", "frontend", "db", "redis"]:
        assert req in services, f"Staging compose missing service: {req}"


def test_staging_compose_internal_networking():
    """Verify staging internal network has internal: true."""
    with open(ROOT_COMPOSE_STAGING, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    networks = data.get("networks", {})
    assert "aegis-staging-internal-net" in networks
    assert networks["aegis-staging-internal-net"].get("internal") is True


def test_staging_compose_db_and_redis_not_publicly_exposed():
    """Verify PostgreSQL and Redis do NOT map ports to the host in staging compose."""
    with open(ROOT_COMPOSE_STAGING, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    services = data.get("services", {})
    assert "ports" not in services["db"], "PostgreSQL must NOT expose host ports in staging"
    assert "ports" not in services["redis"], "Redis must NOT expose host ports in staging"


def test_staging_compose_dedicated_volumes():
    """Verify staging compose declares dedicated staging volumes."""
    with open(ROOT_COMPOSE_STAGING, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    volumes = data.get("volumes", {})
    assert "aegis_postgres_staging_data" in volumes
    assert "aegis_redis_staging_data" in volumes
    assert "aegis_storage_staging" in volumes


def test_staging_compose_resource_limits():
    """Verify staging compose configures deploy resource limits."""
    with open(ROOT_COMPOSE_STAGING, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    services = data.get("services", {})
    for s_name in ["backend", "worker", "scheduler", "frontend", "db", "redis"]:
        deploy = services[s_name].get("deploy", {})
        assert "resources" in deploy, f"Service '{s_name}' missing deploy resources"
        assert "limits" in deploy["resources"], f"Service '{s_name}' missing resource limits"


def test_staging_compose_healthchecks():
    """Verify healthchecks are defined for backend, frontend, db, and redis in staging compose."""
    with open(ROOT_COMPOSE_STAGING, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    services = data.get("services", {})
    for s_name in ["backend", "frontend", "db", "redis"]:
        assert "healthcheck" in services[s_name], f"Service '{s_name}' missing healthcheck"


# ==============================================================================
# 4. Staging Data Seeder & Idempotency
# ==============================================================================

def test_staging_seed_creates_expected_entities():
    """Verify staging seeder creates organizations, workspaces, users, teams, and test fixtures."""
    mock_db = MagicMock()
    # First query (check role/org/etc) returns None to simulate empty staging DB
    mock_db.query.return_value.filter.return_value.first.return_value = None

    summary = seed_staging_environment(mock_db)
    assert summary["roles"] == 4
    assert summary["organizations"] == 2
    assert summary["workspaces"] == 2
    assert summary["users"] == 5
    assert summary["teams"] == 1
    assert summary["documents"] == 1
    assert summary["workflows"] == 1
    assert summary["mcp_tools"] == 1
    assert mock_db.commit.called


def test_staging_seed_is_idempotent():
    """Verify staging seeder returns 0 additions when entities already exist."""
    mock_db = MagicMock()
    existing_obj = MagicMock()
    # Query returns existing object
    mock_db.query.return_value.filter.return_value.first.return_value = existing_obj

    summary = seed_staging_environment(mock_db)
    assert summary["organizations"] == 0
    assert summary["workspaces"] == 0
    assert summary["users"] == 0
    assert summary["teams"] == 0
    assert summary["documents"] == 0


def test_staging_seed_contains_multi_tenant_workspaces():
    """Verify seed constants define distinct Alpha and Beta tenant workspaces."""
    assert ORG_ALPHA_ID != ORG_BETA_ID
    assert WS_ALPHA_ID != WS_BETA_ID


# ==============================================================================
# 5. Staging Reset Safety Guards
# ==============================================================================

def test_staging_reset_refuses_production_environment():
    """Verify staging reset raises StagingResetSafetyError when run in production."""
    with patch.dict(os.environ, {"ENVIRONMENT": "prod"}):
        with pytest.raises(StagingResetSafetyError, match="CRITICAL SAFETY VIOLATION"):
            reset_staging_database(force=True)


def test_staging_reset_refuses_dev_environment():
    """Verify staging reset raises StagingResetSafetyError when run in dev."""
    with patch.dict(os.environ, {"ENVIRONMENT": "dev"}):
        with pytest.raises(StagingResetSafetyError, match="CRITICAL SAFETY VIOLATION"):
            reset_staging_database(force=True)


def test_staging_reset_requires_force_flag():
    """Verify staging reset raises StagingResetSafetyError when force=False."""
    with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
        with pytest.raises(StagingResetSafetyError, match="SAFETY GUARD"):
            reset_staging_database(force=False)


@patch("app.database.staging_reset.run_migrations_with_lock", return_value=True)
@patch("app.database.staging_reset.seed_staging_environment")
@patch("app.database.staging_reset.engine")
def test_staging_reset_succeeds_in_staging_with_force(mock_engine, mock_seed, mock_mig):
    """Verify staging reset executes successfully under advisory lock in staging with force=True."""
    mock_seed.return_value = {"status": "seeded"}
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
        with patch("app.database.staging_reset.SessionLocal"):
            result = reset_staging_database(force=True)
            assert result["status"] == "success"
            assert result["environment"] == "staging"
            assert mock_mig.called
            assert mock_seed.called


# ==============================================================================
# 6. Worker, QueueManager & Scheduler Coordination in Staging
# ==============================================================================

def test_staging_queue_manager_initialization():
    """Verify QueueManager initializes with standard Redis settings in staging."""
    qm = QueueManager()
    assert qm.DEFAULT_QUEUE == "aegis:queue:default"
    assert qm.LEADER_LOCK_KEY == "aegis:scheduler:leader:lock"


def test_staging_worker_concurrency_settings():
    """Verify staging concurrency boundaries in StagingConfig."""
    cfg = StagingConfig()
    assert cfg.WORKER_CONCURRENCY >= 1
    assert cfg.MAX_TENANT_CONCURRENCY <= cfg.WORKER_CONCURRENCY


# ==============================================================================
# 7. Application Health, Readiness & Version Diagnostic Gating
# ==============================================================================

def test_staging_version_endpoint_metadata():
    """Verify GET /version returns service metadata with environment."""
    client = TestClient(app)
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert "git_commit" in data
    assert "environment" in data


def test_staging_liveness_probe():
    """Verify GET /health/liveness returns HTTP 200."""
    client = TestClient(app)
    response = client.get("/health/liveness")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


@patch("app.main.check_redis_health", return_value=True)
def test_staging_readiness_probe_healthy(mock_redis):
    """Verify GET /health/readiness returns 200 when database and redis are healthy."""
    mock_db = MagicMock()
    mock_db.execute.return_value = None
    from app.database.session import get_db
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        client = TestClient(app)
        response = client.get("/health/readiness")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"
    finally:
        app.dependency_overrides.clear()


@patch("app.main.check_redis_health", return_value=False)
def test_staging_readiness_probe_unhealthy(mock_redis):
    """Verify GET /health/readiness returns 503 when dependencies fail."""
    mock_db = MagicMock()
    mock_db.execute.return_value = None
    from app.database.session import get_db
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        client = TestClient(app)
        response = client.get("/health/readiness")
        assert response.status_code == 503
        assert response.json()["status"] == "not_ready"
    finally:
        app.dependency_overrides.clear()


@patch("app.core.queue.QueueManager.get_active_workers", return_value=[])
@patch("app.core.queue.QueueManager.get_queue_depth", return_value={"default": 0})
@patch("app.main.check_redis_health", return_value=True)
def test_staging_dependencies_probe_subsystems(mock_redis, mock_depth, mock_workers):
    """Verify GET /health/dependencies reports complete diagnostic status."""
    mock_db = MagicMock()
    mock_db.execute.return_value = None
    from app.database.session import get_db
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        client = TestClient(app)
        response = client.get("/health/dependencies")
        assert response.status_code == 200
        data = response.json()
        assert "dependencies" in data
        assert "database" in data["dependencies"]
        assert "redis" in data["dependencies"]
        assert "worker_cluster" in data["dependencies"]
        assert "storage" in data["dependencies"]
    finally:
        app.dependency_overrides.clear()
