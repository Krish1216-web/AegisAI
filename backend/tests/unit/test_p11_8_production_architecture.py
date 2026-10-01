"""
Phase 11.8: Production Deployment Architecture Verification Test Suite

Comprehensive automated architecture and configuration verification:
1. TOPOLOGY: Multi-container production stack topology (backend, worker, scheduler, frontend, db, redis)
2. NETWORKING: Strict private internal network (internal: true), no public DB/Redis port exposure
3. CONTAINERS: Resource limits, reservations, healthchecks, and non-root execution (UID 10001)
4. CONFIGURATION: ProductionConfig fail-closed validation (secrets, SQLite rejection, password rules, CORS/Hosts)
5. DATABASE: Linear migration head (019_background_jobs), advisory lock concurrency, no destructive auto-downgrade
6. REDIS & WORKER: Priority queues, heartbeat tracking, horizontal worker scaling, and scheduler leader lock
7. OBSERVABILITY & GATES: Immutable version metadata, liveness/readiness diagnostic gates, security headers
8. MANIFEST INTEGRITY: Validates machine-readable production-architecture.json schema and dependency statuses
"""

import os
import json
import uuid
import yaml
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import (
    BaseConfig,
    ProductionConfig,
    StagingConfig,
    DevelopmentConfig,
    TestConfig,
    get_settings,
    validate_production_configuration
)
from app.database.migration_manager import (
    verify_migration_chain,
    AEGIS_MIGRATION_ADVISORY_LOCK_ID
)
from app.core.queue import QueueManager


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
COMPOSE_PROD_PATH = REPO_ROOT / "docker-compose.prod.yml"
COMPOSE_ROOT_PATH = REPO_ROOT / "docker-compose.yml"
COMPOSE_STAGING_PATH = REPO_ROOT / "docker-compose.staging.yml"
APP_DOCKERFILE_PROD = REPO_ROOT / "docker" / "production" / "app.dockerfile"
FRONTEND_DOCKERFILE_PROD = REPO_ROOT / "docker" / "production" / "frontend.dockerfile"
NGINX_CONF_PROD = REPO_ROOT / "docker" / "production" / "nginx.conf"
MANIFEST_PATH = REPO_ROOT / "backend" / "docs" / "production-architecture.json"


# ==============================================================================
# 1. Topology & Compose Stack Architecture
# ==============================================================================

def test_production_compose_file_exists():
    """Verify docker-compose.prod.yml exists in the repository root."""
    assert COMPOSE_PROD_PATH.exists(), "Missing docker-compose.prod.yml"


def test_production_compose_valid_yaml():
    """Verify docker-compose.prod.yml is valid YAML and has required top-level keys."""
    with open(COMPOSE_PROD_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)
    assert "services" in data
    assert "networks" in data
    assert "volumes" in data


def test_production_compose_services_declared():
    """Verify all 6 core services (backend, worker, scheduler, frontend, db, redis) are declared."""
    with open(COMPOSE_PROD_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    services = data.get("services", {})
    expected = ["backend", "worker", "scheduler", "frontend", "db", "redis"]
    for s in expected:
        assert s in services, f"Production compose stack missing required service: {s}"


def test_production_compose_internal_networking_isolated():
    """Verify production internal network is declared with internal: true."""
    with open(COMPOSE_PROD_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    networks = data.get("networks", {})
    assert "aegis-internal-net" in networks
    assert networks["aegis-internal-net"].get("internal") is True, "aegis-internal-net must be internal: true"


def test_production_compose_no_public_db_or_redis_ports():
    """Verify PostgreSQL and Redis do not bind ports to the host in production compose."""
    with open(COMPOSE_PROD_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    services = data.get("services", {})
    assert "ports" not in services["db"], "PostgreSQL must NOT expose host ports in production"
    assert "ports" not in services["redis"], "Redis must NOT expose host ports in production"


def test_production_compose_resource_limits_declared():
    """Verify CPU and memory limits are configured for all production services."""
    with open(COMPOSE_PROD_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    services = data.get("services", {})
    for s_name in ["backend", "worker", "scheduler", "frontend", "db", "redis"]:
        deploy = services[s_name].get("deploy", {})
        assert "resources" in deploy, f"Service '{s_name}' missing deploy.resources"
        assert "limits" in deploy["resources"], f"Service '{s_name}' missing resource limits"
        assert "cpus" in deploy["resources"]["limits"], f"Service '{s_name}' missing CPU limit"
        assert "memory" in deploy["resources"]["limits"], f"Service '{s_name}' missing memory limit"


def test_production_compose_dedicated_volumes():
    """Verify production compose declares separate persistent volumes."""
    with open(COMPOSE_PROD_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    volumes = data.get("volumes", {})
    assert "aegis_postgres_prod_data" in volumes
    assert "aegis_redis_prod_data" in volumes
    assert "aegis_storage_prod" in volumes
    assert "aegis_logs_prod" in volumes


# ==============================================================================
# 2. Container Hardening & Non-Root Execution
# ==============================================================================

def test_backend_dockerfile_runs_as_non_root():
    """Verify production backend Dockerfile enforces non-root UID 10001 (aegisuser)."""
    assert APP_DOCKERFILE_PROD.exists(), "Missing docker/production/app.dockerfile"
    content = APP_DOCKERFILE_PROD.read_text(encoding="utf-8")
    assert "USER aegisuser" in content or "USER 10001" in content
    assert "10001" in content


def test_frontend_dockerfile_runs_as_non_root():
    """Verify production frontend Dockerfile enforces unprivileged non-root execution."""
    assert FRONTEND_DOCKERFILE_PROD.exists(), "Missing docker/production/frontend.dockerfile"
    content = FRONTEND_DOCKERFILE_PROD.read_text(encoding="utf-8")
    assert "nginx:nginx" in content or "USER" in content or "nginx-unprivileged" in content


def test_nginx_production_security_headers():
    """Verify production Nginx configuration injects security headers."""
    assert NGINX_CONF_PROD.exists(), "Missing docker/production/nginx.conf"
    content = NGINX_CONF_PROD.read_text(encoding="utf-8")
    assert "Strict-Transport-Security" in content
    assert "X-Content-Type-Options" in content
    assert "X-Frame-Options" in content


# ==============================================================================
# 3. Production Configuration Profile & Fail-Closed Validation
# ==============================================================================

def test_production_config_profile_resolution():
    """Verify ENVIRONMENT=prod resolves to ProductionConfig."""
    with patch.dict(os.environ, {"ENVIRONMENT": "prod"}):
        cfg = get_settings()
        assert isinstance(cfg, ProductionConfig)
        assert cfg.ENVIRONMENT == "prod"
        assert cfg.ENABLE_HSTS is True


def test_production_rejects_default_secret_key():
    """Verify production validation rejects placeholder secret keys."""
    cfg = ProductionConfig(SECRET_KEY="SUPER_SECRET_AEGIS_KEY_2026_CHANGE_ME")
    errors = validate_production_configuration(cfg)
    assert any("SECRET_KEY must be securely configured" in e for e in errors)


def test_production_rejects_short_secret_key():
    """Verify production validation rejects secret keys shorter than 32 chars."""
    cfg = ProductionConfig(SECRET_KEY="short_key_12345")
    errors = validate_production_configuration(cfg)
    assert any("too short" in e for e in errors)


def test_production_rejects_sqlite_database():
    """Verify production validation strictly prohibits SQLite."""
    cfg = ProductionConfig(
        SECRET_KEY="a" * 32,
        DATABASE_URL="sqlite:///prod.db"
    )
    errors = validate_production_configuration(cfg)
    assert any("SQLite database is not permitted in production" in e for e in errors)


def test_production_rejects_default_postgres_password():
    """Verify production validation rejects default 'postgres' password."""
    cfg = ProductionConfig(
        SECRET_KEY="a" * 32,
        POSTGRES_PASSWORD="postgres",
        DATABASE_URL=None
    )
    errors = validate_production_configuration(cfg)
    assert any("Production POSTGRES_PASSWORD must not use default" in e for e in errors)


def test_production_rejects_cors_wildcard():
    """Verify production validation rejects wildcard '*' in CORS origins."""
    cfg = ProductionConfig(
        SECRET_KEY="a" * 32,
        POSTGRES_PASSWORD="secure_prod_password_123",
        CORS_ORIGINS=["*"]
    )
    errors = validate_production_configuration(cfg)
    assert any("CORS_ORIGINS must not contain wildcard" in e for e in errors)


def test_production_rejects_allowed_hosts_wildcard():
    """Verify production validation rejects wildcard '*' in ALLOWED_HOSTS."""
    cfg = ProductionConfig(
        SECRET_KEY="a" * 32,
        POSTGRES_PASSWORD="secure_prod_password_123",
        ALLOWED_HOSTS=["*"]
    )
    errors = validate_production_configuration(cfg)
    assert any("ALLOWED_HOSTS must not contain wildcard" in e for e in errors)


def test_production_rejects_invalid_pool_sizes():
    """Verify production validation rejects pool size < 5 and > 100."""
    cfg_low = ProductionConfig(
        SECRET_KEY="a" * 32,
        POSTGRES_PASSWORD="secure_prod_password_123",
        DB_POOL_SIZE=2
    )
    assert any("DB_POOL_SIZE (2) is too low" in e for e in validate_production_configuration(cfg_low))

    cfg_high = ProductionConfig(
        SECRET_KEY="a" * 32,
        POSTGRES_PASSWORD="secure_prod_password_123",
        DB_POOL_SIZE=150
    )
    assert any("DB_POOL_SIZE (150) exceeds safe boundary" in e for e in validate_production_configuration(cfg_high))


def test_production_valid_configuration_passes():
    """Verify a properly configured production profile yields 0 validation errors."""
    cfg = ProductionConfig(
        SECRET_KEY="secure_production_key_2026_enterprise_valid_32chars",
        POSTGRES_PASSWORD="secure_production_password_xyz_123",
        POSTGRES_DB="aegisai_prod",
        DB_POOL_SIZE=20,
        CORS_ORIGINS=["https://app.aegisai.enterprise"],
        ALLOWED_HOSTS=["app.aegisai.enterprise"],
        DOCUMENT_STORAGE_PATH="/workspace/storage"
    )
    errors = validate_production_configuration(cfg)
    assert len(errors) == 0


# ==============================================================================
# 4. Database Migration & Concurrency Control
# ==============================================================================

def test_production_migration_chain_is_linear_and_head_valid():
    """Verify the Alembic migration history is strictly linear and points to 019_background_jobs."""
    chain = verify_migration_chain("alembic.ini")
    assert chain["is_linear"] is True
    assert chain["head"] == "019_background_jobs"
    assert chain["total_revisions"] == 19


def test_production_migration_advisory_lock_id_defined():
    """Verify migration advisory lock ID constant is valid 64-bit integer."""
    assert isinstance(AEGIS_MIGRATION_ADVISORY_LOCK_ID, int)
    assert AEGIS_MIGRATION_ADVISORY_LOCK_ID == 7490001001


# ==============================================================================
# 5. Worker & Distributed Scheduler Architecture
# ==============================================================================

def test_production_queue_manager_queues():
    """Verify QueueManager priority queues and lock constants."""
    qm = QueueManager()
    assert qm.DEFAULT_QUEUE == "aegis:queue:default"
    assert qm.DELAYED_SET == "aegis:queue:delayed"
    assert qm.LEADER_LOCK_KEY == "aegis:scheduler:leader:lock"
    assert qm.WORKER_REGISTRY_PREFIX == "aegis:worker:heartbeat:"


def test_production_worker_concurrency_boundaries():
    """Verify ProductionConfig defines robust concurrency limits."""
    cfg = ProductionConfig()
    assert cfg.WORKER_CONCURRENCY >= 4
    assert cfg.MAX_TENANT_CONCURRENCY <= cfg.WORKER_CONCURRENCY


# ==============================================================================
# 6. Observability, Health & Version Metadata
# ==============================================================================

def test_production_version_endpoint_metadata():
    """Verify /version endpoint exposes build metadata without secrets."""
    client = TestClient(app)
    resp = client.get("/version")
    assert resp.status_code == 200
    data = resp.json()
    assert "service" in data
    assert "version" in data
    assert "git_commit" in data
    assert "environment" in data
    assert "SECRET_KEY" not in data
    assert "password" not in json.dumps(data).lower()


def test_production_liveness_health_probe():
    """Verify /health/liveness returns HTTP 200 alive."""
    client = TestClient(app)
    resp = client.get("/health/liveness")
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"


@patch("app.core.queue.QueueManager.get_active_workers", return_value=[])
@patch("app.core.queue.QueueManager.get_queue_depth", return_value={"default": 0})
@patch("app.main.check_redis_health", return_value=True)
def test_production_dependency_health_probe(mock_redis, mock_depth, mock_workers):
    """Verify /health/dependencies evaluates PostgreSQL, Redis, Worker Cluster, and Storage."""
    mock_db = MagicMock()
    mock_db.execute.return_value = None
    from app.database.session import get_db
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        client = TestClient(app)
        resp = client.get("/health/dependencies")
        assert resp.status_code == 200
        data = resp.json()
        assert "dependencies" in data
        assert "database" in data["dependencies"]
        assert "redis" in data["dependencies"]
        assert "worker_cluster" in data["dependencies"]
        assert "storage" in data["dependencies"]
    finally:
        app.dependency_overrides.clear()


# ==============================================================================
# 7. Production Architecture Manifest Validation
# ==============================================================================

def test_production_manifest_file_exists():
    """Verify backend/docs/production-architecture.json exists."""
    assert MANIFEST_PATH.exists(), "Missing backend/docs/production-architecture.json"


def test_production_manifest_structure():
    """Verify production-architecture.json has required schema and sections."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["environment"] == "production"
    assert "topology" in manifest
    assert "services" in manifest
    assert "deployment_strategy" in manifest
    assert "external_dependencies" in manifest
    assert "verification_summary" in manifest


def test_production_manifest_services_match_compose():
    """Verify manifest services align with production compose stack."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    services = manifest.get("services", {})
    for expected in ["frontend", "backend", "worker", "scheduler", "db", "redis"]:
        assert expected in services, f"Manifest missing service '{expected}'"


def test_production_manifest_dependency_statuses_valid():
    """Verify every external dependency in manifest has a recognized valid status."""
    valid_statuses = {
        "IMPLEMENTED",
        "VERIFIED LOCALLY",
        "REQUIRES CLOUD",
        "REQUIRES DNS",
        "REQUIRES CERTIFICATE",
        "REQUIRES REGISTRY",
        "REQUIRES SECRET MANAGER",
        "NOT YET VERIFIED"
    }
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    deps = manifest.get("external_dependencies", [])
    assert len(deps) >= 8, "Manifest must declare all external dependencies"
    for d in deps:
        assert d["status"] in valid_statuses, f"Invalid dependency status '{d['status']}' in {d['name']}"


def test_production_manifest_no_fabricated_cloud_verification():
    """Verify external infrastructure items are not falsely marked as VERIFIED LOCALLY."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    deps = manifest.get("external_dependencies", [])
    for d in deps:
        if "Cloud Load Balancer" in d["name"]:
            assert d["status"] == "REQUIRES CLOUD"
        elif "DNS Nameserver" in d["name"]:
            assert d["status"] == "REQUIRES DNS"
        elif "Certificate" in d["name"]:
            assert d["status"] == "REQUIRES CERTIFICATE"
        elif "Secrets Manager" in d["name"]:
            assert d["status"] == "REQUIRES SECRET MANAGER"
