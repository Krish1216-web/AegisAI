import os
import yaml
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from app.core.config import (
    BaseConfig,
    ProductionConfig,
    DevelopmentConfig,
    TestConfig,
    validate_production_configuration
)
from app.main import app

# Prevent pytest from treating TestConfig pydantic class as a test suite
TestConfig.__test__ = False

@pytest.fixture
def client():
    return TestClient(app)

# ------------------------------------------------------------------------------
# 1. Production Configuration Validation Tests
# ------------------------------------------------------------------------------

def test_p11_1_production_config_rejects_default_secret():
    cfg = ProductionConfig()
    cfg.SECRET_KEY = "SUPER_SECRET_AEGIS_KEY_2026_CHANGE_ME"
    cfg.POSTGRES_PASSWORD = "strong_random_production_password_2026"
    errors = validate_production_configuration(cfg)
    assert any("SECRET_KEY must be securely configured" in err for err in errors)

def test_p11_1_production_config_rejects_short_secret():
    cfg = ProductionConfig()
    cfg.SECRET_KEY = "short_secret_key"
    cfg.POSTGRES_PASSWORD = "strong_random_production_password_2026"
    errors = validate_production_configuration(cfg)
    assert any("too short" in err for err in errors)

def test_p11_1_production_config_rejects_default_db_password():
    cfg = ProductionConfig()
    cfg.SECRET_KEY = "a_very_secure_random_production_secret_key_12345"
    cfg.POSTGRES_PASSWORD = "postgres"
    cfg.DATABASE_URL = None
    errors = validate_production_configuration(cfg)
    assert any("POSTGRES_PASSWORD must not use default" in err for err in errors)

def test_p11_1_production_config_rejects_cors_wildcard():
    cfg = ProductionConfig()
    cfg.SECRET_KEY = "a_very_secure_random_production_secret_key_12345"
    cfg.POSTGRES_PASSWORD = "strong_random_production_password_2026"
    cfg.CORS_ORIGINS = ["*"]
    errors = validate_production_configuration(cfg)
    assert any("CORS_ORIGINS must not contain wildcard" in err for err in errors)

def test_p11_1_production_config_valid_passes():
    cfg = ProductionConfig()
    cfg.SECRET_KEY = "a_very_secure_random_production_secret_key_12345"
    cfg.POSTGRES_PASSWORD = "strong_random_production_password_2026"
    cfg.CORS_ORIGINS = ["https://aegisai.enterprise.local"]
    cfg.DOCUMENT_STORAGE_PATH = "/workspace/storage"
    errors = validate_production_configuration(cfg)
    assert len(errors) == 0

def test_p11_1_dev_and_test_config_allow_defaults():
    dev_cfg = DevelopmentConfig()
    errors = validate_production_configuration(dev_cfg)
    assert len(errors) == 0

    test_cfg = TestConfig()
    errors = validate_production_configuration(test_cfg)
    assert len(errors) == 0

# ------------------------------------------------------------------------------
# 2. Health, Liveness & Readiness Probe Tests
# ------------------------------------------------------------------------------

def test_p11_1_health_check_endpoint(client):
    with patch("app.main.check_redis_health", return_value=True):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "environment" in data
        assert "dependencies" in data
        # Health check must not leak passwords or secrets
        content_str = response.text.lower()
        assert "super_secret" not in content_str
        assert "postgres:" not in content_str

def test_p11_1_liveness_probe(client):
    response = client.get("/health/liveness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data

def test_p11_1_readiness_probe_healthy(client):
    with patch("app.main.check_redis_health", return_value=True):
        response = client.get("/health/readiness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "ok"
        assert data["redis"] == "ok"

def test_p11_1_readiness_probe_failure_on_db_down(client):
    from app.database.session import get_db
    
    def mock_broken_db():
        mock_session = MagicMock(spec=Session)
        mock_session.execute.side_effect = OperationalError("DB connection lost", None, None)
        yield mock_session

    app.dependency_overrides[get_db] = mock_broken_db
    try:
        response = client.get("/health/readiness")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["database"] == "error"
    finally:
        app.dependency_overrides.pop(get_db, None)

# ------------------------------------------------------------------------------
# 3. Docker Compose & Dockerfile Invariant Tests
# ------------------------------------------------------------------------------

def test_p11_1_docker_compose_files_valid_yaml():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    compose_files = [
        "docker-compose.yml",
        "docker-compose.dev.yml",
        "docker-compose.prod.yml"
    ]
    for filename in compose_files:
        filepath = os.path.join(base_dir, filename)
        assert os.path.isfile(filepath), f"Missing compose file: {filename}"
        with open(filepath, "r", encoding="utf-8") as f:
            parsed = yaml.safe_load(f)
            assert "services" in parsed, f"{filename} missing services section"
            assert "version" in parsed, f"{filename} missing version tag"

def test_p11_1_docker_compose_prod_service_invariants():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    filepath = os.path.join(base_dir, "docker-compose.prod.yml")
    with open(filepath, "r", encoding="utf-8") as f:
        parsed = yaml.safe_load(f)
        services = parsed["services"]
        assert "backend" in services
        assert "frontend" in services
        assert "db" in services
        assert "redis" in services

        # Internal network isolation: database should NOT publish public ports
        assert "ports" not in services["db"], "Production DB should not publish host ports"
        assert "ports" not in services["redis"], "Production Redis should not publish host ports"

def test_p11_1_dockerignore_exclusions():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    dockerignore_path = os.path.join(base_dir, ".dockerignore")
    assert os.path.isfile(dockerignore_path), ".dockerignore must exist"
    with open(dockerignore_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert ".git" in content
        assert "node_modules" in content
        assert "__pycache__" in content
        assert ".env" in content
        assert ".pytest_cache" in content

def test_p11_1_backend_dockerfile_non_root_user():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    dockerfile_path = os.path.join(base_dir, "docker/production/app.dockerfile")
    assert os.path.isfile(dockerfile_path), "docker/production/app.dockerfile must exist"
    with open(dockerfile_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "useradd" in content
        assert "USER aegisuser" in content
        assert "HEALTHCHECK" in content
        assert "storage" in content

# ------------------------------------------------------------------------------
# 4. Production Runtime Dependency & Extractor Regression Tests
# ------------------------------------------------------------------------------

def test_p11_1_production_dependencies_importable():
    """Regression test: verify all runtime dependencies for document parsing and platform are importable."""
    import pypdf
    from pypdf import PdfReader
    import docx
    import pptx
    import openpyxl
    import PIL
    from PIL import Image
    import httpx
    import nest_asyncio
    import pgvector

    assert PdfReader is not None
    assert docx is not None
    assert pptx is not None
    assert openpyxl is not None
    assert Image is not None
    assert httpx is not None
    assert nest_asyncio is not None
    assert pgvector is not None

def test_p11_1_document_extractor_factory_resolution():
    """Regression test: verify DocumentExtractorFactory instantiates all supported format extractors."""
    from app.services.extractors.factory import DocumentExtractorFactory
    from app.services.extractors.pdf import PDFExtractor
    from app.services.extractors.docx import DOCXExtractor
    from app.services.extractors.pptx import PPTXExtractor
    from app.services.extractors.xlsx import XLSXExtractor
    from app.services.extractors.text import TextExtractor
    from app.services.extractors.csv import CSVExtractor
    from app.services.extractors.image import ImageExtractor
    from app.services.extractors.audio_video import AudioVideoExtractor

    assert isinstance(DocumentExtractorFactory.get_extractor("application/pdf", ".pdf"), PDFExtractor)
    assert isinstance(DocumentExtractorFactory.get_extractor("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"), DOCXExtractor)
    assert isinstance(DocumentExtractorFactory.get_extractor("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"), PPTXExtractor)
    assert isinstance(DocumentExtractorFactory.get_extractor("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"), XLSXExtractor)
    assert isinstance(DocumentExtractorFactory.get_extractor("text/plain", ".txt"), TextExtractor)
    assert isinstance(DocumentExtractorFactory.get_extractor("text/csv", ".csv"), CSVExtractor)
    assert isinstance(DocumentExtractorFactory.get_extractor("image/png", ".png"), ImageExtractor)
    assert isinstance(DocumentExtractorFactory.get_extractor("audio/wav", ".wav"), AudioVideoExtractor)
