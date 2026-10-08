"""
Test Suite: Deployment Environment List & CORS/Host Configuration Parsing

Verifies that environment variables for CORS_ORIGINS, ALLOWED_HOSTS, and TRUSTED_PROXIES
are reliably parsed from:
- Single string values (Render single origin deployment)
- Comma-separated strings
- JSON arrays
- Direct Python lists
without triggering pydantic-settings JSONDecodeError / SettingsError.
"""

import os
import pytest
from unittest.mock import patch
from pydantic_settings import BaseSettings

from app.core.config import (
    BaseConfig,
    ProductionConfig,
    DevelopmentConfig,
    validate_production_configuration,
    get_settings
)


def test_render_single_cors_origin_exact_case():
    """Prove that Render's single string CORS_ORIGINS=http://localhost:5173 parses into a list."""
    with patch.dict(os.environ, {
        "CORS_ORIGINS": "http://localhost:5173",
        "ALLOWED_HOSTS": "localhost,127.0.0.1,*.onrender.com,*.vercel.app",
        "TRUSTED_PROXIES": "127.0.0.1"
    }, clear=False):
        cfg = BaseConfig()
        assert isinstance(cfg.CORS_ORIGINS, list)
        assert cfg.CORS_ORIGINS == ["http://localhost:5173"]
        assert isinstance(cfg.ALLOWED_HOSTS, list)
        assert cfg.ALLOWED_HOSTS == ["localhost", "127.0.0.1", "*.onrender.com", "*.vercel.app"]
        assert isinstance(cfg.TRUSTED_PROXIES, list)
        assert cfg.TRUSTED_PROXIES == ["127.0.0.1"]


def test_comma_separated_cors_origins():
    """Prove that comma-separated origins parse into individual trimmed list items."""
    with patch.dict(os.environ, {
        "CORS_ORIGINS": "http://localhost:5173, https://aegisai.vercel.app, https://demo.enterprise.ai"
    }, clear=False):
        cfg = BaseConfig()
        assert cfg.CORS_ORIGINS == [
            "http://localhost:5173",
            "https://aegisai.vercel.app",
            "https://demo.enterprise.ai"
        ]


def test_json_array_cors_origins():
    """Prove that standard JSON-array encoded origins parse correctly."""
    with patch.dict(os.environ, {
        "CORS_ORIGINS": '["http://localhost:5173", "https://aegisai.vercel.app"]'
    }, clear=False):
        cfg = BaseConfig()
        assert cfg.CORS_ORIGINS == [
            "http://localhost:5173",
            "https://aegisai.vercel.app"
        ]


def test_comma_separated_allowed_hosts():
    """Prove that comma-separated ALLOWED_HOSTS parse correctly."""
    with patch.dict(os.environ, {
        "ALLOWED_HOSTS": "localhost, 127.0.0.1, *.onrender.com, *.vercel.app"
    }, clear=False):
        cfg = BaseConfig()
        assert cfg.ALLOWED_HOSTS == ["localhost", "127.0.0.1", "*.onrender.com", "*.vercel.app"]


def test_json_array_allowed_hosts():
    """Prove that JSON-array ALLOWED_HOSTS parse correctly."""
    with patch.dict(os.environ, {
        "ALLOWED_HOSTS": '["localhost", "127.0.0.1", "*.onrender.com"]'
    }, clear=False):
        cfg = BaseConfig()
        assert cfg.ALLOWED_HOSTS == ["localhost", "127.0.0.1", "*.onrender.com"]


def test_comma_separated_trusted_proxies():
    """Prove that comma-separated TRUSTED_PROXIES parse correctly."""
    with patch.dict(os.environ, {
        "TRUSTED_PROXIES": "127.0.0.1, ::1, 10.0.0.0/8"
    }, clear=False):
        cfg = BaseConfig()
        assert cfg.TRUSTED_PROXIES == ["127.0.0.1", "::1", "10.0.0.0/8"]


def test_json_array_trusted_proxies():
    """Prove that JSON-array TRUSTED_PROXIES parse correctly."""
    with patch.dict(os.environ, {
        "TRUSTED_PROXIES": '["127.0.0.1", "::1"]'
    }, clear=False):
        cfg = BaseConfig()
        assert cfg.TRUSTED_PROXIES == ["127.0.0.1", "::1"]


def test_whitespace_and_empty_items_sanitization():
    """Prove that extraneous whitespace and empty comma entries are stripped."""
    with patch.dict(os.environ, {
        "CORS_ORIGINS": " ,  http://localhost:5173  ,, https://app.vercel.app , "
    }, clear=False):
        cfg = BaseConfig()
        assert cfg.CORS_ORIGINS == ["http://localhost:5173", "https://app.vercel.app"]


def test_direct_python_list_instantiation():
    """Prove that passing native Python lists to constructor remains 100% functional."""
    cfg = BaseConfig(
        CORS_ORIGINS=["https://custom-1.com", "https://custom-2.com"],
        ALLOWED_HOSTS=["custom-1.com"],
        TRUSTED_PROXIES=["192.168.1.1"]
    )
    assert cfg.CORS_ORIGINS == ["https://custom-1.com", "https://custom-2.com"]
    assert cfg.ALLOWED_HOSTS == ["custom-1.com"]
    assert cfg.TRUSTED_PROXIES == ["192.168.1.1"]


def test_production_security_validation_with_parsed_env():
    """Prove that production validation properly checks parsed CORS and ALLOWED_HOSTS."""
    # Valid production settings
    valid_cfg = ProductionConfig(
        SECRET_KEY="secure_production_key_2026_enterprise_valid_32chars",
        POSTGRES_PASSWORD="secure_production_password_xyz_123",
        POSTGRES_DB="aegisai_prod",
        DB_POOL_SIZE=20,
        CORS_ORIGINS="https://app.aegisai.enterprise,https://admin.aegisai.enterprise",
        ALLOWED_HOSTS="app.aegisai.enterprise,admin.aegisai.enterprise",
        DOCUMENT_STORAGE_PATH="/workspace/storage"
    )
    errors = validate_production_configuration(valid_cfg)
    assert len(errors) == 0, f"Expected 0 errors, got: {errors}"

    # Invalid wildcard CORS in production
    wildcard_cors_cfg = ProductionConfig(
        SECRET_KEY="secure_production_key_2026_enterprise_valid_32chars",
        POSTGRES_PASSWORD="secure_production_password_xyz_123",
        CORS_ORIGINS="*"
    )
    cors_errors = validate_production_configuration(wildcard_cors_cfg)
    assert any("CORS_ORIGINS must not contain wildcard" in e for e in cors_errors)

    # Invalid wildcard Host in production
    wildcard_host_cfg = ProductionConfig(
        SECRET_KEY="secure_production_key_2026_enterprise_valid_32chars",
        POSTGRES_PASSWORD="secure_production_password_xyz_123",
        ALLOWED_HOSTS="*"
    )
    host_errors = validate_production_configuration(wildcard_host_cfg)
    assert any("ALLOWED_HOSTS must not contain wildcard" in e for e in host_errors)


def test_local_sqlite_configuration_remains_valid():
    """Prove that local development defaults and SQLite URL resolution are untouched."""
    cfg = DevelopmentConfig()
    assert cfg.ENVIRONMENT == "dev"
    assert "sqlite" in cfg.get_database_url() or "postgresql" in cfg.get_database_url()


def test_database_url_normalization_postgres_and_psycopg_schemes():
    """Verify that postgres://, postgresql+psycopg://, postgresql://, etc. schemes normalize to canonical postgresql+psycopg2://."""
    # 1. postgres:// scheme
    cfg1 = BaseConfig(DATABASE_URL="postgres://postgres.abc:pwd@aws-0-ap-south-1.pooler.supabase.com:5432/postgres")
    assert cfg1.get_database_url() == "postgresql+psycopg2://postgres.abc:pwd@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"

    # 2. postgresql+psycopg:// scheme
    cfg2 = BaseConfig(DATABASE_URL="postgresql+psycopg://postgres.abc:pwd@aws-0-ap-south-1.pooler.supabase.com:5432/postgres")
    assert cfg2.get_database_url() == "postgresql+psycopg2://postgres.abc:pwd@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"

    # 3. Standard postgresql:// scheme
    cfg3 = BaseConfig(DATABASE_URL="postgresql://postgres.abc:pwd@aws-0-ap-south-1.pooler.supabase.com:5432/postgres")
    assert cfg3.get_database_url() == "postgresql+psycopg2://postgres.abc:pwd@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"

    # 4. postgresql+psycopg3:// scheme
    cfg4 = BaseConfig(DATABASE_URL="postgresql+psycopg3://postgres.abc:pwd@aws-0-ap-south-1.pooler.supabase.com:5432/postgres")
    assert cfg4.get_database_url() == "postgresql+psycopg2://postgres.abc:pwd@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"

    # 5. postgresql+psycopg2:// scheme (unchanged)
    cfg5 = BaseConfig(DATABASE_URL="postgresql+psycopg2://postgres.abc:pwd@aws-0-ap-south-1.pooler.supabase.com:5432/postgres")
    assert cfg5.get_database_url() == "postgresql+psycopg2://postgres.abc:pwd@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"

    # 6. Preserves query parameters and special characters in credentials
    cfg6 = BaseConfig(DATABASE_URL="postgresql+psycopg://postgres.abc:p%40ss%3Aword%21@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require&pgbouncer=true")
    assert cfg6.get_database_url() == "postgresql+psycopg2://postgres.abc:p%40ss%3Aword%21@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require&pgbouncer=true"

    # 7. SQLite scheme remains unchanged
    cfg7 = BaseConfig(DATABASE_URL="sqlite:///./aegisai.db")
    assert cfg7.get_database_url() == "sqlite:///./aegisai.db"


def test_safe_database_info_diagnostic_never_logs_passwords():
    """Verify safe diagnostic info reports connection metadata without leaking passwords."""
    from app.core.config import get_safe_database_info
    raw_url = "postgresql+psycopg://postgres.demo_user:super_secret_password_1234@db.render.internal:5432/aegisai_prod?sslmode=require"
    info = get_safe_database_info(raw_url)
    assert info["configured"] is True
    assert info["scheme"] == "postgresql+psycopg"
    assert info["hostname"] == "db.render.internal"
    assert info["port"] == 5432
    assert info["database"] == "aegisai_prod"
    assert info["has_credentials"] is True
    # Ensure password and username values are nowhere in serialized representation
    assert "super_secret_password_1234" not in str(info)


def test_python_runtime_version_declarations():
    """Verify that repository and backend Python runtime files pin Python 3.12."""
    from pathlib import Path
    backend_dir = Path(__file__).resolve().parent.parent.parent
    repo_root = backend_dir.parent

    # Check root .python-version and runtime.txt
    root_pv = repo_root / ".python-version"
    backend_pv = backend_dir / ".python-version"
    root_rt = repo_root / "runtime.txt"
    backend_rt = backend_dir / "runtime.txt"

    assert root_pv.exists(), "Missing root .python-version file"
    assert "3.12" in root_pv.read_text()

    assert backend_pv.exists(), "Missing backend .python-version file"
    assert "3.12" in backend_pv.read_text()

    assert root_rt.exists(), "Missing root runtime.txt file"
    assert "3.12" in root_rt.read_text()

    assert backend_rt.exists(), "Missing backend runtime.txt file"
    assert "3.12" in backend_rt.read_text()


def test_render_dependency_requirements_declares_psycopg2():
    """Verify backend/requirements.txt directly declares psycopg2-binary for Render."""
    from pathlib import Path
    backend_dir = Path(__file__).resolve().parent.parent.parent
    req_file = backend_dir / "requirements.txt"
    assert req_file.exists(), "Missing backend/requirements.txt"
    content = req_file.read_text()
    assert "psycopg2-binary" in content, "psycopg2-binary not declared in backend/requirements.txt"


def test_sqlalchemy_dialect_resolution_is_psycopg2_for_all_postgres_schemes():
    """Verify that all PostgreSQL URL schemes resolve to SQLAlchemy's psycopg2 driver."""
    from sqlalchemy.engine import make_url

    test_urls = [
        "postgres://postgres.abc:pwd@aws-0-ap-south-1.pooler.supabase.com:5432/postgres",
        "postgresql://postgres.abc:pwd@aws-0-ap-south-1.pooler.supabase.com:5432/postgres",
        "postgresql+psycopg://postgres.abc:pwd@aws-0-ap-south-1.pooler.supabase.com:5432/postgres",
        "postgresql+psycopg3://postgres.abc:pwd@aws-0-ap-south-1.pooler.supabase.com:5432/postgres",
        "postgresql+psycopg2://postgres.abc:pwd@aws-0-ap-south-1.pooler.supabase.com:5432/postgres",
    ]

    for raw_url in test_urls:
        cfg = BaseConfig(DATABASE_URL=raw_url)
        resolved_url = cfg.get_database_url()
        url_obj = make_url(resolved_url)
        dialect_cls = url_obj.get_dialect()
        assert dialect_cls.name == "postgresql"
        assert dialect_cls.driver == "psycopg2", f"Expected psycopg2 driver for {raw_url}, got {dialect_cls.driver}"
        assert dialect_cls.driver != "psycopg", f"Error: resolved to psycopg3 driver for {raw_url}"


def test_alembic_engine_configuration_guarantees_psycopg2_driver():
    """Verify that Alembic's engine_from_config resolves to psycopg2 and never psycopg3."""
    from sqlalchemy import engine_from_config, pool
    from app.core.config import BaseConfig

    raw_urls = [
        "postgres://postgres.test:secret@aws-0-ap-south-1.pooler.supabase.com:5432/postgres",
        "postgresql://postgres.test:secret@aws-0-ap-south-1.pooler.supabase.com:5432/postgres",
        "postgresql+psycopg://postgres.test:secret@aws-0-ap-south-1.pooler.supabase.com:5432/postgres",
        "postgresql+psycopg3://postgres.test:secret@aws-0-ap-south-1.pooler.supabase.com:5432/postgres",
        "postgresql+psycopg2://postgres.test:secret@aws-0-ap-south-1.pooler.supabase.com:5432/postgres",
    ]

    for raw_url in raw_urls:
        cfg = BaseConfig(DATABASE_URL=raw_url)
        normalized_url = cfg.get_database_url()
        configuration = {"sqlalchemy.url": normalized_url}
        eng = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
        assert eng.dialect.name == "postgresql"
        assert eng.dialect.driver == "psycopg2"
        assert eng.dialect.driver != "psycopg"

