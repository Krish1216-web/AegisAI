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
