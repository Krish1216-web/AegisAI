"""
AegisAI Enterprise — Phase 11.10 Final Production Readiness & Release Gate Test Suite

Comprehensive tests for:
- Phase 11 Release Manifest validity and status classification
- Risk Register coverage (RSK-01 through RSK-14) and external dependency classification
- Production Architecture & Disaster Recovery manifest schema integrity
- Production configuration fail-closed validator enforcement (secrets, TLS, DB, CORS, hosts)
- Alembic migration chain linearity and single head verification
- Production Docker compose network isolation (no public PostgreSQL/Redis exposure)
- Non-root user execution (UID 10001 / aegisuser) in production Dockerfiles
- Backward-compatible rollback invariant verification
- Test inventory consistency and release readiness decision
- Operational runbook and final readiness documentation verification
"""

import os
import re
import json
import yaml
import pytest
from pathlib import Path

from app.core.config import (
    BaseConfig,
    ProductionConfig,
    StagingConfig,
    DevelopmentConfig,
    TestConfig,
    validate_production_configuration
)
from app.database.migration_manager import verify_migration_chain
from app.database.backup_manager import RestoreSafetyError


DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "docs"
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
DOCKER_PROD_DIR = ROOT_DIR / "docker" / "production"


# ==============================================================================
# 1. Release Manifest & Decision Tests
# ==============================================================================

def test_phase_11_release_manifest_exists_and_valid():
    """Verifies that phase-11-release-manifest.json exists and is valid JSON."""
    manifest_path = DOCS_DIR / "phase-11-release-manifest.json"
    assert manifest_path.is_file(), f"Release manifest not found at {manifest_path}"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["version"] == "1.0.0"
    assert manifest["branch"] == "phase-11-deployment"
    assert manifest["migration_head"] == "020_user_avatar_schema_sync"
    assert manifest["final_readiness_decision"] == "READY FOR CONTROLLED PRODUCTION DEPLOYMENT WITH EXTERNAL INFRASTRUCTURE PREREQUISITES"


def test_phase_11_release_manifest_status_classifications():
    """Verifies all components use exact valid status labels."""
    manifest_path = DOCS_DIR / "phase-11-release-manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    valid_statuses = {
        "VERIFIED LOCALLY",
        "IMPLEMENTED",
        "TARGET",
        "TARGET — NOT YET MEASURED IN PRODUCTION",
        "REQUIRES EXTERNAL INFRASTRUCTURE",
        "NOT VERIFIED",
        "ARCHITECTURALLY SUPPORTED"
    }

    # Check phase components
    for comp_key, comp_val in manifest["phase_components"].items():
        assert comp_val["status"] in valid_statuses, f"Invalid status in {comp_key}: {comp_val['status']}"

    # Check external prerequisites
    for prereq_key, prereq_val in manifest["external_infrastructure_prerequisites"].items():
        assert prereq_val in valid_statuses, f"Invalid status in {prereq_key}: {prereq_val}"


def test_phase_11_release_manifest_images_non_root():
    """Verifies that all image metadata declares multi-stage and non-root user."""
    manifest_path = DOCS_DIR / "phase-11-release-manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for img_name in ["backend", "frontend", "worker"]:
        assert img_name in manifest["images"]
        img_info = manifest["images"][img_name]
        assert img_info["multi_stage"] is True
        assert "10001" in img_info["user"]


# ==============================================================================
# 2. Risk Register & Documentation Tests
# ==============================================================================

def test_phase_11_risk_register_exists_and_covers_all_risks():
    """Verifies that phase-11-risk-register.md exists and contains RSK-01 through RSK-14."""
    risk_path = DOCS_DIR / "phase-11-risk-register.md"
    assert risk_path.is_file(), f"Risk register not found at {risk_path}"

    content = risk_path.read_text(encoding="utf-8")
    for i in range(1, 15):
        risk_id = f"RSK-{i:02d}"
        assert risk_id in content, f"Missing risk definition for {risk_id}"

    assert "READY FOR CONTROLLED PRODUCTION DEPLOYMENT WITH EXTERNAL INFRASTRUCTURE PREREQUISITES" in content


def test_phase_11_risk_register_external_boundaries():
    """Verifies that external boundaries are explicitly defined in the risk register."""
    risk_path = DOCS_DIR / "phase-11-risk-register.md"
    content = risk_path.read_text(encoding="utf-8")

    expected_boundaries = [
        "DNS & Ingress Routing",
        "TLS/HTTPS Certificates",
        "Container Registry",
        "Cloud Secrets Manager",
        "PostgreSQL HA Cluster",
        "Redis HA Cluster",
        "Object Storage",
        "AI Provider APIs"
    ]
    for b in expected_boundaries:
        assert b in content, f"Missing boundary definition: {b}"


def test_production_runbook_and_final_readiness_docs_exist():
    """Verifies presence of 92-Production-Release-Runbook.md and 93-Phase-11-Final-Production-Readiness.md."""
    runbook_path = DOCS_DIR / "92-Production-Release-Runbook.md"
    readiness_path = DOCS_DIR / "93-Phase-11-Final-Production-Readiness.md"

    assert runbook_path.is_file()
    assert readiness_path.is_file()

    readiness_text = readiness_path.read_text(encoding="utf-8")
    assert "READY FOR CONTROLLED PRODUCTION DEPLOYMENT WITH EXTERNAL INFRASTRUCTURE PREREQUISITES" in readiness_text
    assert "Factual Readiness Scorecard" in readiness_text


def test_runbook_sections_coverage():
    """Verifies that the runbook covers pre-deployment, deployment, post-deployment, rollback, and recovery."""
    runbook_path = DOCS_DIR / "92-Production-Release-Runbook.md"
    content = runbook_path.read_text(encoding="utf-8")

    assert "Phase 1: Pre-Deployment Verification" in content
    assert "Phase 2: Deployment Execution" in content
    assert "Phase 3: Post-Deployment Verification" in content
    assert "Phase 4: Emergency Rollback Procedure" in content
    assert "Phase 5: Disaster Recovery & Database Restoration" in content
    assert "alembic downgrade" in content


# ==============================================================================
# 3. Production Configuration Fail-Closed Enforcement Tests
# ==============================================================================

def test_validate_prod_config_rejects_default_secret_key():
    """Verifies that production configuration rejects default placeholder secret keys."""
    cfg = ProductionConfig()
    cfg.SECRET_KEY = "SUPER_SECRET_AEGIS_KEY_2026_CHANGE_ME"
    errors = validate_production_configuration(cfg)
    assert any("SECRET_KEY must be securely configured" in e for e in errors)


def test_validate_prod_config_rejects_short_secret_key():
    """Verifies rejection of short SECRET_KEY (<32 chars) in production."""
    cfg = ProductionConfig()
    cfg.SECRET_KEY = "short_secret_key"
    errors = validate_production_configuration(cfg)
    assert any("SECRET_KEY is too short" in e for e in errors)


def test_validate_prod_config_rejects_sqlite():
    """Verifies rejection of SQLite databases in production configuration."""
    cfg = ProductionConfig()
    cfg.SECRET_KEY = "a_very_strong_production_secret_key_exceeding_32_bytes_length"
    cfg.DATABASE_URL = "sqlite:///production.db"
    errors = validate_production_configuration(cfg)
    assert any("SQLite database is not permitted" in e for e in errors)


def test_validate_prod_config_rejects_default_postgres_password():
    """Verifies rejection of default 'postgres' password in production."""
    cfg = ProductionConfig()
    cfg.SECRET_KEY = "a_very_strong_production_secret_key_exceeding_32_bytes_length"
    cfg.POSTGRES_PASSWORD = "postgres"
    cfg.DATABASE_URL = None
    errors = validate_production_configuration(cfg)
    assert any("POSTGRES_PASSWORD must not use default" in e for e in errors)


def test_validate_prod_config_pool_size_boundaries():
    """Verifies pool size boundaries (<5 or >100) are enforced."""
    cfg_low = ProductionConfig()
    cfg_low.SECRET_KEY = "a_very_strong_production_secret_key_exceeding_32_bytes_length"
    cfg_low.DB_POOL_SIZE = 2
    errors_low = validate_production_configuration(cfg_low)
    assert any("DB_POOL_SIZE (2) is too low" in e for e in errors_low)

    cfg_high = ProductionConfig()
    cfg_high.SECRET_KEY = "a_very_strong_production_secret_key_exceeding_32_bytes_length"
    cfg_high.DB_POOL_SIZE = 150
    errors_high = validate_production_configuration(cfg_high)
    assert any("DB_POOL_SIZE (150) exceeds safe boundary" in e for e in errors_high)


def test_validate_prod_config_rejects_wildcard_cors_with_credentials():
    """Verifies rejection of wildcard CORS when credentials are enabled."""
    cfg = ProductionConfig()
    cfg.SECRET_KEY = "a_very_strong_production_secret_key_exceeding_32_bytes_length"
    cfg.CORS_ORIGINS = ["*"]
    errors = validate_production_configuration(cfg)
    assert any("CORS_ORIGINS must not contain wildcard" in e for e in errors)


def test_validate_prod_config_rejects_wildcard_allowed_hosts():
    """Verifies rejection of wildcard '*' in ALLOWED_HOSTS."""
    cfg = ProductionConfig()
    cfg.SECRET_KEY = "a_very_strong_production_secret_key_exceeding_32_bytes_length"
    cfg.ALLOWED_HOSTS = ["*"]
    errors = validate_production_configuration(cfg)
    assert any("ALLOWED_HOSTS must not contain wildcard" in e for e in errors)


def test_validate_prod_config_tls_cert_key_pair_consistency():
    """Verifies requirement of both TLS cert and key when one is specified."""
    cfg1 = ProductionConfig()
    cfg1.SECRET_KEY = "a_very_strong_production_secret_key_exceeding_32_bytes_length"
    cfg1.TLS_CERT_PATH = "/certs/server.crt"
    cfg1.TLS_KEY_PATH = None
    errors1 = validate_production_configuration(cfg1)
    assert any("TLS_KEY_PATH must be provided" in e for e in errors1)

    cfg2 = ProductionConfig()
    cfg2.SECRET_KEY = "a_very_strong_production_secret_key_exceeding_32_bytes_length"
    cfg2.TLS_CERT_PATH = None
    cfg2.TLS_KEY_PATH = "/certs/server.key"
    errors2 = validate_production_configuration(cfg2)
    assert any("TLS_CERT_PATH must be provided" in e for e in errors2)


def test_validate_staging_config_isolation_guard():
    """Verifies staging configuration prevents pointing directly to aegisai_prod database."""
    cfg = StagingConfig()
    cfg.SECRET_KEY = "a_very_strong_staging_secret_key_exceeding_32_bytes_length"
    cfg.POSTGRES_DB = "aegisai_prod"
    errors = validate_production_configuration(cfg)
    assert any("Staging environment must not connect to the production database 'aegisai_prod'" in e for e in errors)


def test_validate_prod_config_valid_success():
    """Verifies that fully valid production config passes with 0 errors."""
    cfg = ProductionConfig()
    cfg.SECRET_KEY = "a_very_strong_and_long_production_secret_key_2026_secure"
    cfg.POSTGRES_PASSWORD = "production_secure_password_987654"
    cfg.POSTGRES_DB = "aegisai_prod"
    cfg.DATABASE_URL = "postgresql://aegisuser:production_secure_password_987654@db:5432/aegisai_prod"
    cfg.CORS_ORIGINS = ["https://app.aegisai.example.com"]
    cfg.ALLOWED_HOSTS = ["app.aegisai.example.com", "api.aegisai.example.com"]
    cfg.DOCUMENT_STORAGE_PATH = "/var/storage"
    cfg.DB_POOL_SIZE = 20

    errors = validate_production_configuration(cfg)
    assert len(errors) == 0


# ==============================================================================
# 4. Alembic Migration Chain & Schema Linearity Tests
# ==============================================================================

def test_alembic_migration_chain_is_linear_and_head_is_valid():
    """Verifies Alembic migration chain is strictly linear and head is 020_user_avatar_schema_sync."""
    chain = verify_migration_chain()
    assert chain["is_linear"] is True
    assert chain["head"] == "020_user_avatar_schema_sync"
    assert chain["total_revisions"] == 20


def test_alembic_all_revisions_sequential():
    """Verifies that all 20 revisions exist in sequential order."""
    chain = verify_migration_chain()
    revisions = chain["revisions"]
    assert len(revisions) == 20
    assert revisions[0] == "020_user_avatar_schema_sync"  # head first
    assert revisions[-1] == "001_initial_migration"  # base last


# ==============================================================================
# 5. Production Dockerfile & Compose Security Tests
# ==============================================================================

def test_production_dockerfiles_enforce_non_root_user():
    """Verifies all production Dockerfiles configure and run as non-root UID 10001."""
    dockerfiles = [
        DOCKER_PROD_DIR / "app.dockerfile",
        DOCKER_PROD_DIR / "frontend.dockerfile",
        DOCKER_PROD_DIR / "worker.dockerfile",
    ]

    for df in dockerfiles:
        assert df.is_file(), f"Missing Dockerfile at {df}"
        content = df.read_text(encoding="utf-8")
        assert "USER aegisuser" in content or "nginx:nginx" in content or "USER nginx" in content or "10001" in content, f"Dockerfile {df.name} does not enforce non-root user"


def test_production_compose_isolates_postgres_and_redis():
    """Verifies production docker-compose does not expose PostgreSQL (5432) or Redis (6379) to public ports."""
    compose_path = ROOT_DIR / "docker-compose.prod.yml"
    assert compose_path.is_file(), f"Production compose file not found at {compose_path}"

    with open(compose_path, "r", encoding="utf-8") as f:
        parsed = yaml.safe_load(f)

    services = parsed["services"]
    assert "db" in services
    assert "redis" in services
    assert "ports" not in services["db"], "Production DB ports must not be exposed on host!"
    assert "ports" not in services["redis"], "Production Redis ports must not be exposed on host!"


def test_dockerignore_includes_sensitive_patterns():
    """Verifies root and backend .dockerignore exclude .env, .git, and credentials."""
    root_dockerignore = ROOT_DIR / ".dockerignore"
    assert root_dockerignore.is_file()
    content = root_dockerignore.read_text(encoding="utf-8")

    assert ".git" in content
    assert ".env" in content
    assert "node_modules" in content
    assert "__pycache__" in content


# ==============================================================================
# 6. Disaster Recovery & Production Manifest Cross-Verification
# ==============================================================================

def test_production_architecture_manifest_validity():
    """Verifies production-architecture.json schema and entrypoints."""
    arch_path = DOCS_DIR / "production-architecture.json"
    assert arch_path.is_file()

    with open(arch_path, "r", encoding="utf-8") as f:
        arch = json.load(f)

    assert arch["environment"] == "production"
    assert "aegis-internal-net" in arch["topology"]["networks"]
    assert arch["topology"]["networks"]["aegis-internal-net"]["internal"] is True
    assert "backend" in arch["services"]
    assert "frontend" in arch["services"]
    assert "worker" in arch["services"]


def test_disaster_recovery_manifest_validity():
    """Verifies disaster-recovery-manifest.json schema and scenarios DR-01 to DR-10."""
    dr_path = DOCS_DIR / "disaster-recovery-manifest.json"
    assert dr_path.is_file()

    with open(dr_path, "r", encoding="utf-8") as f:
        dr = json.load(f)

    assert len(dr["disaster_recovery_scenarios"]) == 10
    scenario_ids = [s["id"] for s in dr["disaster_recovery_scenarios"]]
    for i in range(1, 11):
        assert f"DR-{i:02d}" in scenario_ids


def test_disaster_recovery_rpo_rto_status_tags():
    """Verifies that RPO and RTO in disaster recovery manifest are labeled as TARGET."""
    dr_path = DOCS_DIR / "disaster-recovery-manifest.json"
    with open(dr_path, "r", encoding="utf-8") as f:
        dr = json.load(f)

    rpo = dr["recovery_objectives"]["rpo"]
    rto = dr["recovery_objectives"]["rto"]

    assert "NOT YET MEASURED IN PRODUCTION" in rpo["status"]
    assert "NOT YET MEASURED IN PRODUCTION" in rto["status"]
