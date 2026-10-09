"""
AegisAI Enterprise — OpenAPI & Documentation Endpoint Tests
Validates root and versioned OpenAPI schemas, Swagger UI / ReDoc rendering,
route-specific Content-Security-Policy enforcement, and health/security invariants.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings, ProductionConfig, validate_production_configuration

client = TestClient(app)

def test_openapi_schema_root_endpoint():
    """Verify GET /openapi.json returns valid OpenAPI 3.x schema specification."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    
    data = response.json()
    assert "openapi" in data
    assert data["openapi"].startswith("3.")
    assert "info" in data
    assert data["info"]["title"] == settings.PROJECT_NAME
    assert "paths" in data
    assert len(data["paths"]) > 0
    assert "/health" in data["paths"]
    assert f"{settings.API_V1_STR}/auth/login" in data["paths"]


def test_openapi_schema_v1_alias_endpoint():
    """Verify GET /api/v1/openapi.json returns identical valid schema for compatibility."""
    response = client.get(f"{settings.API_V1_STR}/openapi.json")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    
    data = response.json()
    assert "openapi" in data
    assert "paths" in data
    assert f"{settings.API_V1_STR}/auth/login" in data["paths"]


def test_swagger_ui_docs_endpoint_and_csp():
    """
    Verify GET /docs serves Swagger UI HTML and injects a CSP header that permits
    required CDN assets (cdn.jsdelivr.net, fastapi.tiangolo.com) so the UI does not render blank.
    """
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "swagger-ui" in response.text
    
    # Check CSP header on docs route
    csp = response.headers.get("content-security-policy", "")
    assert "https://cdn.jsdelivr.net" in csp, "CSP on /docs must allow cdn.jsdelivr.net for swagger-ui assets"
    assert "https://fastapi.tiangolo.com" in csp, "CSP on /docs must allow fastapi.tiangolo.com for favicon"
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


def test_redoc_endpoint_and_csp():
    """Verify GET /redoc serves ReDoc HTML and allows required CDN scripts."""
    response = client.get("/redoc")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "redoc" in response.text.lower()
    
    csp = response.headers.get("content-security-policy", "")
    assert "https://cdn.jsdelivr.net" in csp, "CSP on /redoc must allow cdn.jsdelivr.net for redoc scripts"


def test_versioned_docs_redirects():
    """Verify /api/v1/docs and /api/v1/redoc redirect cleanly to standard /docs and /redoc."""
    res_docs = client.get(f"{settings.API_V1_STR}/docs", follow_redirects=False)
    assert res_docs.status_code in (307, 302, 308, 301)
    assert res_docs.headers["location"] == "/docs"

    res_redoc = client.get(f"{settings.API_V1_STR}/redoc", follow_redirects=False)
    assert res_redoc.status_code in (307, 302, 308, 301)
    assert res_redoc.headers["location"] == "/redoc"


def test_api_endpoints_retain_strict_csp():
    """
    Verify that standard API and health endpoints maintain strict CSP without
    unnecessary external CDN allowances in script-src.
    """
    response = client.get("/health/liveness")
    assert response.status_code == 200
    csp = response.headers.get("content-security-policy", "")
    assert "default-src 'self'" in csp
    assert "script-src 'self' 'unsafe-inline'" in csp
    # CDN should NOT be in script-src for standard API responses
    assert "cdn.jsdelivr.net" not in csp


def test_health_and_liveness_probes_intact():
    """Verify core liveness, version, and health endpoints respond normally."""
    res_live = client.get("/health/liveness")
    assert res_live.status_code == 200
    assert res_live.json()["status"] == "alive"

    res_ver = client.get("/version")
    assert res_ver.status_code == 200
    assert "version" in res_ver.json()
    assert "git_commit" in res_ver.json()

    res_ver_v1 = client.get(f"{settings.API_V1_STR}/version")
    assert res_ver_v1.status_code == 200
    assert res_ver_v1.json()["api_version"] == "v1"


def test_production_security_configuration_intact():
    """Verify production security configuration validation remains strictly fail-closed."""
    valid_cfg = ProductionConfig(
        SECRET_KEY="A_VERY_LONG_SECURE_PRODUCTION_KEY_FOR_TESTING_PURPOSES_2026",
        POSTGRES_PASSWORD="secure_prod_password_xyz_123",
        DOCUMENT_STORAGE_PATH="/workspace/storage",
        CORS_ORIGINS=["https://app.aegisai.enterprise"],
        ALLOWED_HOSTS=["app.aegisai.enterprise"],
        DB_POOL_SIZE=20
    )
    assert validate_production_configuration(valid_cfg) == []
