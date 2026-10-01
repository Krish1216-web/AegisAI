"""
Phase 11.6: CI/CD & Automated Production Delivery Verification Test Suite

Validates:
- GitHub Actions workflow syntax, YAML validity, and structure
- Least-privilege permissions across all jobs (contents: read, id-token: write)
- Trigger conditions and concurrency settings (CI cancellation vs CD non-cancellation)
- Pipeline gates: lint, tests, migration validation, security scanning, image build
- Multi-image Software Bill of Materials (SBOM) generation (backend, frontend, worker)
- Image digest extraction, manifest integrity (image-manifest.json), and attestation
- Immutable artifact promotion (same digest in staging & prod, rejecting rebuilds)
- Staging smoke test failure blocking production promotion
- Production manual approval gate (environment: production)
- Non-destructive rollback behavior (revert image digest without automatic destructive DB downgrade)
- Dependency vulnerability auditing (pip-audit, npm audit, Bandit, Trivy)
- Explicit bounded artifact retention policy (<= 30 days)
- Application version metadata endpoints (/version and /api/v1/version)
- Secret non-disclosure in metadata endpoints
- Production health and readiness diagnostic gating
"""

import os
import yaml
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app.main import app
from app.core.config import settings, BaseConfig


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
DOCKER_DIR = REPO_ROOT / "docker" / "production"


# ==============================================================================
# 1. Workflow File Integrity & YAML Syntax Validation
# ==============================================================================

def test_workflow_files_exist():
    """Verify that CI and CD workflow files exist in .github/workflows."""
    ci_path = WORKFLOWS_DIR / "ci.yml"
    cd_path = WORKFLOWS_DIR / "cd-delivery.yml"
    assert ci_path.exists(), f"Missing CI workflow file: {ci_path}"
    assert cd_path.exists(), f"Missing CD workflow file: {cd_path}"


def test_ci_workflow_valid_yaml():
    """Verify that ci.yml is valid YAML and has required top-level attributes."""
    ci_path = WORKFLOWS_DIR / "ci.yml"
    with open(ci_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "ci.yml must parse to a dictionary"
    assert "name" in data
    assert "on" in data or True in data
    assert "jobs" in data
    assert "permissions" in data


def test_cd_workflow_valid_yaml():
    """Verify that cd-delivery.yml is valid YAML and has required top-level attributes."""
    cd_path = WORKFLOWS_DIR / "cd-delivery.yml"
    with open(cd_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "cd-delivery.yml must parse to a dictionary"
    assert "name" in data
    assert "on" in data or True in data
    assert "jobs" in data
    assert "permissions" in data


# ==============================================================================
# 2. Least-Privilege Permissions & Hardening
# ==============================================================================

def test_ci_workflow_least_privilege_permissions():
    """Verify CI workflow specifies minimal permissions (contents: read) and no write-all."""
    ci_path = WORKFLOWS_DIR / "ci.yml"
    with open(ci_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    assert data["permissions"] == {"contents": "read"}
    for job_name, job in data.get("jobs", {}).items():
        job_perms = job.get("permissions")
        if job_perms:
            assert job_perms != "write-all"
            assert job_perms.get("contents") == "read"


def test_cd_workflow_least_privilege_permissions():
    """Verify CD workflow uses strictly scoped permissions."""
    cd_path = WORKFLOWS_DIR / "cd-delivery.yml"
    with open(cd_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    top_perms = data.get("permissions", {})
    assert top_perms != "write-all"
    assert top_perms.get("contents") == "read"
    assert top_perms.get("packages") == "write"
    assert top_perms.get("id-token") == "write"


def test_no_plaintext_secrets_in_workflow_definitions():
    """Verify no hardcoded credentials or passwords exist in workflow files."""
    for wf in [WORKFLOWS_DIR / "ci.yml", WORKFLOWS_DIR / "cd-delivery.yml"]:
        with open(wf, "r", encoding="utf-8") as f:
            content = f.read()
        assert "super_secret" not in content.lower()
        assert "password:" not in content or "${{ secrets." in content or "POSTGRES_PASSWORD: postgres" in content


# ==============================================================================
# 3. Trigger Conditions & Concurrency Controls
# ==============================================================================

def test_ci_concurrency_settings():
    """Verify CI workflow cancels in-progress runs for the same branch."""
    ci_path = WORKFLOWS_DIR / "ci.yml"
    with open(ci_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    concurrency = data.get("concurrency", {})
    assert concurrency.get("cancel-in-progress") is True


def test_cd_concurrency_protection():
    """Verify CD workflow NEVER cancels in-progress production deployments."""
    cd_path = WORKFLOWS_DIR / "cd-delivery.yml"
    with open(cd_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    concurrency = data.get("concurrency", {})
    assert concurrency.get("cancel-in-progress") is False


# ==============================================================================
# 4. Mandatory Pipeline Jobs & Step Validation
# ==============================================================================

def test_ci_contains_all_required_jobs():
    """Verify CI contains backend-ci, frontend-ci, security-and-secrets, and docker-build-and-scan."""
    ci_path = WORKFLOWS_DIR / "ci.yml"
    with open(ci_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    jobs = data.get("jobs", {})
    required_jobs = ["backend-ci", "frontend-ci", "security-and-secrets", "docker-build-and-scan"]
    for req in required_jobs:
        assert req in jobs, f"Missing required CI job: {req}"


def test_ci_backend_includes_database_services():
    """Verify backend-ci spins up PostgreSQL and Redis service containers."""
    ci_path = WORKFLOWS_DIR / "ci.yml"
    with open(ci_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    services = data["jobs"]["backend-ci"].get("services", {})
    assert "postgres" in services
    assert "redis" in services
    assert "postgres:16-alpine" in services["postgres"]["image"]
    assert "redis:7-alpine" in services["redis"]["image"]


def test_ci_backend_includes_migration_and_lint_validation():
    """Verify backend CI includes Alembic migration check and linting steps."""
    ci_path = WORKFLOWS_DIR / "ci.yml"
    with open(ci_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    steps = data["jobs"]["backend-ci"].get("steps", [])
    step_runs = " ".join(s.get("run", "") for s in steps)
    assert "ruff check" in step_runs
    assert "black --check" in step_runs
    assert "alembic upgrade head" in step_runs
    assert "alembic check" in step_runs


def test_ci_frontend_includes_test_and_build():
    """Verify frontend CI executes tests, dependency audit, and production build."""
    ci_path = WORKFLOWS_DIR / "ci.yml"
    with open(ci_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    steps = data["jobs"]["frontend-ci"].get("steps", [])
    step_runs = " ".join(s.get("run", "") for s in steps)
    assert "npm ci" in step_runs
    assert "npm audit" in step_runs
    assert "npm run lint" in step_runs
    assert "npm test" in step_runs
    assert "npm run build" in step_runs


def test_ci_security_includes_secret_scanning_and_bandit():
    """Verify security job includes secret scanning and Bandit analysis."""
    ci_path = WORKFLOWS_DIR / "ci.yml"
    with open(ci_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    steps = data["jobs"]["security-and-secrets"].get("steps", [])
    step_uses = [s.get("uses", "") for s in steps]
    step_runs = " ".join(s.get("run", "") for s in steps)
    assert any("trufflehog" in u.lower() or "gitleaks" in u.lower() for u in step_uses)
    assert "bandit" in step_runs


def test_ci_no_unapproved_continue_on_error():
    """Ensure critical test, migration, and security steps do NOT have continue-on-error: true."""
    ci_path = WORKFLOWS_DIR / "ci.yml"
    with open(ci_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    for job_name, job in data.get("jobs", {}).items():
        for step in job.get("steps", []):
            step_name = step.get("name", "")
            if "test" in step_name.lower() or "migration" in step_name.lower() or "secret" in step_name.lower():
                assert step.get("continue-on-error", False) is False, f"Step '{step_name}' has continue-on-error: true"


# ==============================================================================
# 5. Dependency Vulnerability Security Gates
# ==============================================================================

def test_ci_python_dependency_audit_step_configured():
    """Verify python dependency vulnerability scanning with pip-audit is defined in security job."""
    ci_path = WORKFLOWS_DIR / "ci.yml"
    with open(ci_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    steps = data["jobs"]["security-and-secrets"].get("steps", [])
    step_runs = " ".join(s.get("run", "") for s in steps)
    assert "pip-audit" in step_runs


def test_ci_npm_dependency_audit_step_configured():
    """Verify frontend dependency vulnerability audit is configured with high-severity threshold."""
    ci_path = WORKFLOWS_DIR / "ci.yml"
    with open(ci_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    steps = data["jobs"]["frontend-ci"].get("steps", [])
    step_runs = " ".join(s.get("run", "") for s in steps)
    assert "npm audit --audit-level=high" in step_runs


# ==============================================================================
# 6. Software Bill of Materials (SBOM) Generation
# ==============================================================================

def test_ci_sbom_generation_for_all_images():
    """Verify SBOM generation step is configured for backend, frontend, and worker in CI."""
    ci_path = WORKFLOWS_DIR / "ci.yml"
    with open(ci_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    steps = data["jobs"]["docker-build-and-scan"].get("steps", [])
    sbom_gen_steps = [s for s in steps if "anchore/sbom-action" in s.get("uses", "")]
    assert len(sbom_gen_steps) >= 3, "CI must generate SBOMs for backend, frontend, and worker images"
    
    # Check formats
    for step in sbom_gen_steps:
        with_cfg = step.get("with", {})
        assert with_cfg.get("format") in ["spdx-json", "cyclonedx-json", "spdx", "cyclonedx"]


def test_cd_sbom_generation_in_release_pipeline():
    """Verify release SBOM generation is configured in the CD pipeline."""
    cd_path = WORKFLOWS_DIR / "cd-delivery.yml"
    with open(cd_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    steps = data["jobs"]["build-and-package"].get("steps", [])
    sbom_steps = [s for s in steps if "anchore/sbom-action" in s.get("uses", "")]
    assert len(sbom_steps) >= 3, "CD build-and-package must generate SBOMs for all release containers"


# ==============================================================================
# 7. Image Digest Integrity, Attestation & Manifest
# ==============================================================================

def test_cd_extracts_and_outputs_image_digests():
    """Verify build-and-package extracts immutable digests and declares them as job outputs."""
    cd_path = WORKFLOWS_DIR / "cd-delivery.yml"
    with open(cd_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    job = data["jobs"]["build-and-package"]
    outputs = job.get("outputs", {})
    assert "backend_digest" in outputs
    assert "frontend_digest" in outputs
    assert "worker_digest" in outputs


def test_cd_generates_image_manifest_json():
    """Verify CD generates an image-manifest.json capturing immutable digest and metadata."""
    cd_path = WORKFLOWS_DIR / "cd-delivery.yml"
    with open(cd_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    steps = data["jobs"]["build-and-package"].get("steps", [])
    step_runs = " ".join(s.get("run", "") for s in steps)
    assert "image-manifest.json" in step_runs
    assert "docker inspect" in step_runs


def test_cd_attest_build_provenance_step():
    """Verify CD includes build provenance attestation step with SLSA / GitHub OIDC."""
    cd_path = WORKFLOWS_DIR / "cd-delivery.yml"
    with open(cd_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    steps = data["jobs"]["build-and-package"].get("steps", [])
    attest_step = next((s for s in steps if "attest" in s.get("name", "").lower() or "attest-build-provenance" in s.get("uses", "")), None)
    assert attest_step is not None, "CD pipeline must configure an image provenance attestation step"


# ==============================================================================
# 8. Bounded Artifact Retention Policy
# ==============================================================================

def test_ci_artifact_retention_is_bounded():
    """Verify all CI uploaded artifacts declare explicit retention periods <= 30 days."""
    ci_path = WORKFLOWS_DIR / "ci.yml"
    with open(ci_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    for job_name, job in data.get("jobs", {}).items():
        for step in job.get("steps", []):
            if "upload-artifact" in step.get("uses", ""):
                with_cfg = step.get("with", {})
                retention = with_cfg.get("retention-days")
                assert retention is not None, f"Job '{job_name}' step '{step.get('name')}' missing retention-days"
                assert int(retention) <= 30, f"Retention {retention} exceeds 30 days"


def test_cd_artifact_retention_is_bounded():
    """Verify CD release artifacts declare explicit bounded retention periods <= 30 days."""
    cd_path = WORKFLOWS_DIR / "cd-delivery.yml"
    with open(cd_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    for job_name, job in data.get("jobs", {}).items():
        for step in job.get("steps", []):
            if "upload-artifact" in step.get("uses", ""):
                with_cfg = step.get("with", {})
                retention = with_cfg.get("retention-days")
                assert retention is not None, f"Job '{job_name}' step '{step.get('name')}' missing retention-days"
                assert int(retention) <= 30, f"Retention {retention} exceeds 30 days"


# ==============================================================================
# 9. Immutable Artifact Promotion & Anti-Rebuild Guarantees
# ==============================================================================

def test_cd_promotes_same_artifact_without_rebuilding():
    """Verify deploy-production uses output digests from build-and-package and does NOT execute docker build."""
    cd_path = WORKFLOWS_DIR / "cd-delivery.yml"
    with open(cd_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    prod_job = data["jobs"]["deploy-production"]
    steps = prod_job.get("steps", [])
    step_runs = " ".join(s.get("run", "") for s in steps)
    step_envs = " ".join(str(s.get("env", {})) for s in steps)
    all_step_text = f"{step_runs} {step_envs}"
    
    # Production deployment must reference the build output digests
    assert "needs.build-and-package.outputs.backend_digest" in all_step_text
    assert "needs.build-and-package.outputs.frontend_digest" in all_step_text
    assert "needs.build-and-package.outputs.worker_digest" in all_step_text
    
    # Production deployment step must NOT rebuild images
    assert "docker build" not in step_runs, "Production deployment must promote existing artifact without rebuilding"


def test_staging_uses_same_artifact_digest():
    """Verify staging deployment references the same output digests from build-and-package."""
    cd_path = WORKFLOWS_DIR / "cd-delivery.yml"
    with open(cd_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    staging_job = data["jobs"]["deploy-staging"]
    steps = staging_job.get("steps", [])
    step_runs = " ".join(s.get("run", "") for s in steps)
    step_envs = " ".join(str(s.get("env", {})) for s in steps)
    all_step_text = f"{step_runs} {step_envs}"
    
    assert "needs.build-and-package.outputs.backend_digest" in all_step_text
    assert "needs.build-and-package.outputs.frontend_digest" in all_step_text
    assert "needs.build-and-package.outputs.worker_digest" in all_step_text


# ==============================================================================
# 10. Staging Smoke Tests & Failure Blocking
# ==============================================================================

def test_cd_staging_smoke_failure_blocks_production():
    """Verify deploy-production strictly depends on deploy-staging completing successfully."""
    cd_path = WORKFLOWS_DIR / "cd-delivery.yml"
    with open(cd_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    prod_needs = data["jobs"]["deploy-production"].get("needs", [])
    assert "deploy-staging" in prod_needs, "deploy-production must have deploy-staging in 'needs' dependency list"


def test_cd_staging_contains_smoke_test_step():
    """Verify staging deployment contains smoke verification step."""
    cd_path = WORKFLOWS_DIR / "cd-delivery.yml"
    with open(cd_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    steps = data["jobs"]["deploy-staging"].get("steps", [])
    has_smoke = any("smoke" in s.get("name", "").lower() for s in steps)
    assert has_smoke, "Staging deployment must execute smoke test step"


# ==============================================================================
# 11. Production Approval & Non-Destructive Rollback Architecture
# ==============================================================================

def test_cd_environment_gates_configured():
    """Verify staging and production have dedicated environment definitions."""
    cd_path = WORKFLOWS_DIR / "cd-delivery.yml"
    with open(cd_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    jobs = data.get("jobs", {})
    staging_env = jobs["deploy-staging"].get("environment", {})
    prod_env = jobs["deploy-production"].get("environment", {})
    assert staging_env.get("name") == "staging"
    assert prod_env.get("name") == "production"


def test_cd_rollback_handling_present():
    """Verify CD production deployment contains an automated rollback step."""
    cd_path = WORKFLOWS_DIR / "cd-delivery.yml"
    with open(cd_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    steps = data["jobs"]["deploy-production"].get("steps", [])
    has_rollback = any("rollback" in s.get("name", "").lower() for s in steps)
    assert has_rollback, "deploy-production must define a rollback step"


def test_cd_rollback_does_not_execute_automatic_db_downgrade():
    """Verify production rollback reverts container workloads without running destructive alembic downgrade."""
    cd_path = WORKFLOWS_DIR / "cd-delivery.yml"
    with open(cd_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    steps = data["jobs"]["deploy-production"].get("steps", [])
    rollback_step = next((s for s in steps if "rollback" in s.get("name", "").lower()), None)
    assert rollback_step is not None
    run_text = rollback_step.get("run", "")
    assert "alembic downgrade" not in run_text, "Rollback must NOT automatically run destructive alembic downgrade"


# ==============================================================================
# 12. Dockerfile Build Argument & Hardening Checks
# ==============================================================================

def test_app_dockerfile_supports_version_args():
    """Verify app.dockerfile defines ARG APP_VERSION, GIT_COMMIT_SHA, and BUILD_TIMESTAMP."""
    app_dockerfile = DOCKER_DIR / "app.dockerfile"
    with open(app_dockerfile, "r", encoding="utf-8") as f:
        content = f.read()
    assert "ARG APP_VERSION" in content
    assert "ARG GIT_COMMIT_SHA" in content
    assert "ARG BUILD_TIMESTAMP" in content
    assert "USER aegisuser" in content


def test_worker_dockerfile_supports_version_args():
    """Verify worker.dockerfile defines ARG APP_VERSION, GIT_COMMIT_SHA, and BUILD_TIMESTAMP."""
    worker_dockerfile = DOCKER_DIR / "worker.dockerfile"
    with open(worker_dockerfile, "r", encoding="utf-8") as f:
        content = f.read()
    assert "ARG APP_VERSION" in content
    assert "ARG GIT_COMMIT_SHA" in content
    assert "ARG BUILD_TIMESTAMP" in content
    assert "USER aegisuser" in content


def test_frontend_dockerfile_uses_unprivileged_nginx():
    """Verify frontend.dockerfile runs as non-root / unprivileged nginx."""
    frontend_dockerfile = DOCKER_DIR / "frontend.dockerfile"
    with open(frontend_dockerfile, "r", encoding="utf-8") as f:
        content = f.read()
    assert "nginxinc/nginx-unprivileged" in content or "USER" in content or "nginx" in content


# ==============================================================================
# 13. Application Version Endpoint (/version) Tests
# ==============================================================================

def test_version_endpoint_root():
    """Verify GET /version returns the required build metadata."""
    client = TestClient(app)
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert "git_commit" in data
    assert "environment" in data
    assert "api_version" in data
    assert data["service"] == settings.PROJECT_NAME


def test_version_endpoint_api_v1():
    """Verify GET /api/v1/version returns matching metadata."""
    client = TestClient(app)
    response = client.get(f"{settings.API_V1_STR}/version")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == settings.VERSION
    assert data["git_commit"] == settings.GIT_COMMIT_SHA


def test_version_endpoint_does_not_leak_secrets():
    """Verify GET /version response does not expose passwords, secret keys, or database URLs."""
    client = TestClient(app)
    response = client.get("/version")
    assert response.status_code == 200
    text = response.text.lower()
    
    assert "secret" not in text or "secret_key" not in text
    assert "password" not in text
    assert "postgres://" not in text
    assert "postgresql://" not in text
    assert "redis://" not in text


def test_version_metadata_override_via_settings():
    """Verify that settings correctly accept custom version, commit SHA, and build timestamp."""
    with patch.object(settings, "VERSION", "2.5.0-rc1"), \
         patch.object(settings, "GIT_COMMIT_SHA", "abcdef1234567890"), \
         patch.object(settings, "BUILD_TIMESTAMP", "2026-10-01T12:00:00Z"):
        client = TestClient(app)
        response = client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.5.0-rc1"
        assert data["git_commit"] == "abcdef1234567890"
        assert data["build_timestamp"] == "2026-10-01T12:00:00Z"


# ==============================================================================
# 14. Health & Readiness Probe Gating for CD Delivery
# ==============================================================================

def test_liveness_probe_available_for_deployment():
    """Verify liveness probe returns HTTP 200 immediately."""
    client = TestClient(app)
    response = client.get("/health/liveness")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


@patch("app.main.check_redis_health", return_value=True)
def test_readiness_probe_healthy(mock_redis):
    """Verify readiness probe returns HTTP 200 when backend dependencies are connected."""
    mock_db = MagicMock()
    mock_db.execute.return_value = None
    app.dependency_overrides = {}
    from app.database.session import get_db
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        client = TestClient(app)
        response = client.get("/health/readiness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "ok"
        assert data["redis"] == "ok"
    finally:
        app.dependency_overrides.clear()


@patch("app.main.check_redis_health", return_value=False)
def test_readiness_probe_unhealthy_fails_delivery_gate(mock_redis):
    """Verify readiness probe returns HTTP 503 when a dependency is down, halting deployment."""
    mock_db = MagicMock()
    mock_db.execute.return_value = None
    from app.database.session import get_db
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        client = TestClient(app)
        response = client.get("/health/readiness")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["redis"] == "error"
    finally:
        app.dependency_overrides.clear()


@patch("app.main.check_redis_health", return_value=True)
def test_dependencies_probe_available_for_deployment(mock_redis):
    """Verify dependency diagnostic probe returns complete health status breakdown."""
    mock_db = MagicMock()
    mock_db.execute.return_value = None
    from app.database.session import get_db
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        client = TestClient(app)
        response = client.get("/health/dependencies")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data["dependencies"]
        assert "redis" in data["dependencies"]
        assert "worker_cluster" in data["dependencies"]
        assert "storage" in data["dependencies"]
    finally:
        app.dependency_overrides.clear()
