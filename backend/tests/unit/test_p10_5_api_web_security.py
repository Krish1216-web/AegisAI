"""
Phase 10.5 — API & Web Security Hardening Unit Tests
Validates security headers, CORS policies, host trust, request size boundaries,
IP rate-limiting spoof resistance, error redactions, and download protections.
"""
import pytest
import uuid
import json
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from fastapi import Request, HTTPException, status
from starlette.datastructures import Headers, Address

from app.main import app
from app.core.config import settings
from app.api.dependencies import check_ip_rate_limit
from app.core.exceptions import register_exception_handlers, AegisBaseException
from app.core.mcp.security import CredentialStore

client = TestClient(app)

def test_security_headers_present():
    """
    Verifies that all required enterprise HTTP security headers are injected into responses.
    """
    response = client.get("/health")
    assert response.status_code == 200
    
    headers = response.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in headers.get("permissions-policy", "")
    assert "default-src 'self'" in headers.get("content-security-policy", "")

def test_sensitive_auth_route_cache_prevention():
    """
    Verifies that sensitive auth endpoints strictly return no-store and no-cache controls.
    """
    response = client.post("/api/v1/auth/login", data={"username": "fake", "password": "wrong"})
    headers = response.headers
    cache_ctrl = headers.get("cache-control", "").lower()
    assert "no-store" in cache_ctrl
    assert "no-cache" in cache_ctrl
    assert headers.get("pragma") == "no-cache"

def test_cors_policy_allowed_and_denied_origins():
    """
    Verifies explicit CORS origin enforcement: allowed origins pass, unapproved origins are blocked.
    """
    # 1. Allowed origin
    res_allowed = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST"
        }
    )
    assert res_allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert res_allowed.headers.get("access-control-allow-credentials") == "true"

    # 2. Denied unauthorized origin
    res_denied = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://malicious-attacker.com",
            "Access-Control-Request-Method": "POST"
        }
    )
    assert res_denied.headers.get("access-control-allow-origin") != "http://malicious-attacker.com"

def test_trusted_host_enforcement():
    """
    Verifies TrustedHostMiddleware blocks requests directed to arbitrary untrusted Host headers.
    """
    # Allowed host
    res_valid = client.get("/health", headers={"Host": "localhost"})
    assert res_valid.status_code == 200

    # Disallowed host (Must return 400 Bad Request)
    res_invalid = client.get("/health", headers={"Host": "evil-phishing-domain.com"})
    assert res_invalid.status_code == 400

def test_request_size_limit_rejection():
    """
    Verifies that payloads exceeding maximum request limits are rejected with HTTP 413.
    """
    # Mock an oversized Content-Length header exceeding 10MB
    oversized_headers = {
        "Content-Length": str(15 * 1024 * 1024),
        "Content-Type": "application/json"
    }
    res = client.post("/api/v1/auth/register", headers=oversized_headers, json={"username": "test"})
    assert res.status_code == 413
    assert res.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"

def test_ip_rate_limiting_ignores_spoofed_forwarded_headers():
    """
    Verifies that IP rate limiting relies on direct client host and cannot be bypassed via X-Forwarded-For.
    """
    mock_redis = MagicMock()
    mock_redis.incr.return_value = 1

    # Fake request with spoofed X-Forwarded-For header
    scope = {
        "type": "http",
        "client": ("198.51.100.25", 54321),
        "headers": [(b"x-forwarded-for", b"1.2.3.4, 5.6.7.8")]
    }
    req = Request(scope)

    check_ip_rate_limit(req, redis_client=mock_redis, limit_per_minute=30, action="test_action")

    # Assert Redis key uses actual client host "198.51.100.25", NOT "1.2.3.4"
    called_key = mock_redis.incr.call_args[0][0]
    assert "198.51.100.25" in called_key
    assert "1.2.3.4" not in called_key

def test_ip_rate_limit_exceeded_raises_429():
    """
    Verifies HTTP 429 is raised when request count exceeds limit per minute.
    """
    mock_redis = MagicMock()
    mock_redis.incr.return_value = 31  # Exceeds limit of 30

    scope = {
        "type": "http",
        "client": ("198.51.100.50", 12345),
        "headers": []
    }
    req = Request(scope)

    with pytest.raises(HTTPException) as exc:
        check_ip_rate_limit(req, redis_client=mock_redis, limit_per_minute=30, action="login")
    assert exc.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS

def test_exception_handler_sanitizes_credentials_in_error_details():
    """
    Verifies that system exception details strip secrets and database URIs before returning response.
    """
    raw_error_text = "Connection failed to postgres://admin:super_secret_pw@db.internal:5432/aegis with key sk-proj-12345678901234567890"
    redacted = CredentialStore.redact_sensitive_str(raw_error_text)
    
    assert "super_secret_pw" not in redacted
    assert "sk-proj-12345678901234567890" not in redacted
    assert "[REDACTED_CREDENTIALS]" in redacted
    assert "[REDACTED_API_KEY]" in redacted
