"""
AegisAI Enterprise — Phase 11.3 Networking, Reverse Proxy & HTTPS Unit Tests
Validates Nginx reverse proxy configuration, TLS 1.2/1.3 hardening, HTTP->HTTPS redirect,
trusted proxy client IP resolution, security headers, upload boundaries, and network isolation.
"""

import os
import re
import pytest
import unittest.mock as mock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from app.core.config import BaseConfig, ProductionConfig, DevelopmentConfig, TestConfig, validate_production_configuration
from app.core.network import is_trusted_proxy, get_trusted_client_ip
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.request_limits import RequestSizeLimitMiddleware

TestConfig.__test__ = False

def _read_nginx_conf() -> str:
    candidates = [
        "../docker/production/nginx.conf",
        "../../docker/production/nginx.conf",
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "docker", "production", "nginx.conf")
    ]
    for c in candidates:
        if os.path.exists(c):
            with open(c, "r", encoding="utf-8") as f:
                return f.read()
    pytest.fail("Could not find docker/production/nginx.conf")

def _read_compose_prod() -> str:
    candidates = [
        "../docker-compose.prod.yml",
        "../../docker-compose.prod.yml",
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "docker-compose.prod.yml")
    ]
    for c in candidates:
        if os.path.exists(c):
            with open(c, "r", encoding="utf-8") as f:
                return f.read()
    pytest.fail("Could not find docker-compose.prod.yml")

def test_nginx_tls_protocols_and_ciphers():
    """Verify that Nginx is configured strictly for TLS 1.2 and 1.3 with modern ciphers."""
    conf = _read_nginx_conf()
    assert "ssl_protocols TLSv1.2 TLSv1.3;" in conf
    assert "SSLv2" not in conf
    assert "SSLv3" not in conf
    assert "TLSv1.0" not in conf
    assert "TLSv1.1" not in conf
    assert "ssl_ciphers" in conf
    assert "ECDHE" in conf
    assert "ssl_prefer_server_ciphers off;" in conf
    assert "ssl_session_tickets off;" in conf

def test_nginx_http_to_https_redirect():
    """Verify that port 80 listener issues 301 redirects to HTTPS while allowing health checks."""
    conf = _read_nginx_conf()
    assert "listen 80;" in conf
    assert "return 301 https://$host$request_uri;" in conf
    assert "location /health" in conf
    assert "location /live" in conf
    assert "location /ready" in conf

def test_nginx_security_headers_present():
    """Verify that Nginx injects standard enterprise web security headers."""
    conf = _read_nginx_conf()
    assert 'add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;' in conf
    assert 'add_header X-Frame-Options "DENY" always;' in conf
    assert 'add_header X-Content-Type-Options "nosniff" always;' in conf
    assert 'add_header Referrer-Policy "strict-origin-when-cross-origin" always;' in conf
    assert 'add_header Permissions-Policy' in conf

def test_nginx_sse_and_websocket_configuration():
    """Verify unbuffered streaming for SSE and upgrade handling for WebSockets."""
    conf = _read_nginx_conf()
    assert "proxy_buffering off;" in conf
    assert "proxy_cache off;" in conf
    assert "chunked_transfer_encoding on;" in conf
    assert "proxy_read_timeout 86400s;" in conf
    assert "proxy_set_header Upgrade $http_upgrade;" in conf
    assert 'proxy_set_header Connection "upgrade";' in conf

def test_nginx_upload_limit_and_timeouts():
    """Verify 50M upload boundary for documents with extended read timeout."""
    conf = _read_nginx_conf()
    assert "location /api/v1/documents/upload" in conf
    assert "client_max_body_size 50M;" in conf
    assert "proxy_read_timeout 300s;" in conf

def test_nginx_spa_routing_and_revalidation():
    """Verify SPA fallback and no-cache policy on index.html."""
    conf = _read_nginx_conf()
    assert "try_files $uri $uri/ /index.html;" in conf
    assert "location = /index.html" in conf
    assert 'add_header Cache-Control "no-cache, no-store, must-revalidate";' in conf

def test_trusted_proxy_helper_matching():
    """Verify is_trusted_proxy matches loopback, private ranges, and explicit IPs."""
    assert is_trusted_proxy("127.0.0.1") is True
    assert is_trusted_proxy("::1") is True
    assert is_trusted_proxy("localhost") is True
    assert is_trusted_proxy("172.18.0.5") is True  # In 172.16.0.0/12
    assert is_trusted_proxy("10.0.1.20") is True   # In 10.0.0.0/8
    assert is_trusted_proxy("192.168.1.100") is True # In 192.168.0.0/16
    assert is_trusted_proxy("203.0.113.50") is False  # Public IP
    assert is_trusted_proxy("unknown") is False
    assert is_trusted_proxy("") is False

def test_client_ip_resolution_direct():
    """Verify direct connection without proxy returns direct socket peer IP."""
    mock_req = mock.MagicMock(spec=Request)
    mock_req.client.host = "203.0.113.45"
    mock_req.headers = {}
    
    ip = get_trusted_client_ip(mock_req)
    assert ip == "203.0.113.45"

def test_client_ip_resolution_trusted_x_forwarded_for():
    """Verify trusted reverse proxy forwards genuine client IP via X-Forwarded-For."""
    mock_req = mock.MagicMock(spec=Request)
    mock_req.client.host = "172.18.0.2"  # Trusted Docker network proxy
    mock_req.headers = {"x-forwarded-for": "198.51.100.88"}
    
    ip = get_trusted_client_ip(mock_req)
    assert ip == "198.51.100.88"

def test_client_ip_resolution_trusted_chained_forwarded():
    """Verify chained X-Forwarded-For selects originating client IP."""
    mock_req = mock.MagicMock(spec=Request)
    mock_req.client.host = "127.0.0.1"
    mock_req.headers = {"x-forwarded-for": "203.0.113.99, 10.0.0.2, 172.16.0.3"}
    
    ip = get_trusted_client_ip(mock_req)
    assert ip == "203.0.113.99"

def test_client_ip_resolution_untrusted_spoof_ignored():
    """Verify untrusted peer attempting to spoof X-Forwarded-For has header ignored."""
    mock_req = mock.MagicMock(spec=Request)
    mock_req.client.host = "198.51.100.5"  # Untrusted external client
    mock_req.headers = {"x-forwarded-for": "10.0.0.1"}
    
    ip = get_trusted_client_ip(mock_req)
    # Must ignore spoofed header and return direct peer
    assert ip == "198.51.100.5"

def test_client_ip_resolution_trusted_x_real_ip():
    """Verify trusted proxy X-Real-IP fallback."""
    mock_req = mock.MagicMock(spec=Request)
    mock_req.client.host = "10.0.5.1"
    mock_req.headers = {"x-real-ip": "198.51.100.77"}
    
    ip = get_trusted_client_ip(mock_req)
    assert ip == "198.51.100.77"

def test_production_config_rejects_wildcard_allowed_hosts():
    """Verify that wildcard ALLOWED_HOSTS is rejected in production configuration."""
    cfg = ProductionConfig(
        SECRET_KEY="A_VERY_LONG_SECURE_PRODUCTION_KEY_FOR_TESTING_PURPOSES_2026",
        POSTGRES_PASSWORD="secure_prod_password_123",
        DOCUMENT_STORAGE_PATH="/workspace/storage",
        CORS_ORIGINS=["https://app.aegisai.enterprise"],
        ALLOWED_HOSTS=["*"]
    )
    errors = validate_production_configuration(cfg)
    assert any("ALLOWED_HOSTS must not contain wildcard '*'" in e for e in errors)

def test_production_config_rejects_wildcard_trusted_proxies():
    """Verify that wildcard TRUSTED_PROXIES is rejected in production configuration."""
    cfg = ProductionConfig(
        SECRET_KEY="A_VERY_LONG_SECURE_PRODUCTION_KEY_FOR_TESTING_PURPOSES_2026",
        POSTGRES_PASSWORD="secure_prod_password_123",
        DOCUMENT_STORAGE_PATH="/workspace/storage",
        CORS_ORIGINS=["https://app.aegisai.enterprise"],
        TRUSTED_PROXIES=["*"]
    )
    errors = validate_production_configuration(cfg)
    assert any("TRUSTED_PROXIES must not contain wildcard '*'" in e for e in errors)

def test_production_config_tls_paths_pair_validation():
    """Verify that TLS_CERT_PATH and TLS_KEY_PATH must both be provided if one is configured."""
    cfg_cert_only = ProductionConfig(
        SECRET_KEY="A_VERY_LONG_SECURE_PRODUCTION_KEY_FOR_TESTING_PURPOSES_2026",
        POSTGRES_PASSWORD="secure_prod_password_123",
        DOCUMENT_STORAGE_PATH="/workspace/storage",
        CORS_ORIGINS=["https://app.aegisai.enterprise"],
        TLS_CERT_PATH="/etc/nginx/certs/tls.crt"
    )
    errors = validate_production_configuration(cfg_cert_only)
    assert any("TLS_KEY_PATH must be provided" in e for e in errors)

    cfg_key_only = ProductionConfig(
        SECRET_KEY="A_VERY_LONG_SECURE_PRODUCTION_KEY_FOR_TESTING_PURPOSES_2026",
        POSTGRES_PASSWORD="secure_prod_password_123",
        DOCUMENT_STORAGE_PATH="/workspace/storage",
        CORS_ORIGINS=["https://app.aegisai.enterprise"],
        TLS_KEY_PATH="/etc/nginx/certs/tls.key"
    )
    errors = validate_production_configuration(cfg_key_only)
    assert any("TLS_CERT_PATH must be provided" in e for e in errors)

def test_security_headers_middleware_invariants():
    """Verify SecurityHeadersMiddleware injects required headers into response."""
    test_app = FastAPI()
    test_app.add_middleware(SecurityHeadersMiddleware)
    
    @test_app.get("/api/v1/test")
    def sample_endpoint():
        return {"ok": True}
        
    @test_app.get("/api/v1/auth/session")
    def auth_endpoint():
        return {"user": "alice"}

    client = TestClient(test_app)
    
    res = client.get("/api/v1/test")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert "content-security-policy" in res.headers

    res_auth = client.get("/api/v1/auth/session")
    assert "no-store" in res_auth.headers["cache-control"]

def test_docker_compose_prod_service_isolation():
    """Verify that database and redis services in docker-compose.prod.yml do not expose public ports."""
    compose_text = _read_compose_prod()
    import yaml
    compose_data = yaml.safe_load(compose_text)
    
    services = compose_data.get("services", {})
    
    # DB must have no host ports
    assert "ports" not in services.get("db", {}), "Production database must not expose host ports"
    # Redis must have no host ports
    assert "ports" not in services.get("redis", {}), "Production Redis must not expose host ports"
    # Backend must have no host ports (only proxy routes traffic)
    assert "ports" not in services.get("backend", {}), "Production backend should not publish host ports directly"
    
    # Frontend must expose 80 and 443
    frontend_ports = services.get("frontend", {}).get("ports", [])
    assert any("80:80" in str(p) for p in frontend_ports)
    assert any("443:443" in str(p) for p in frontend_ports)
