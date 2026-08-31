import pytest
from app.core.mcp.security import CredentialStore

def test_credential_masking():
    assert CredentialStore.mask_credential("sk-1234567890abcdef") == "sk-••••def"
    assert CredentialStore.mask_credential("short") == "••••••••"
    assert CredentialStore.mask_credential("") == ""
    assert CredentialStore.mask_credential(None) == ""

def test_sanitize_auth_config():
    auth_config = {
        "provider": "openai",
        "api_key": "sk-1234567890abcdef",
        "bearer_token": "token-xyz-secret-999",
        "client_secret": "my-client-secret-123",
        "public_endpoint": "https://api.example.com",
        "nested": {
            "password": "super-secret-password"
        }
    }
    sanitized = CredentialStore.sanitize_auth_config(auth_config)
    assert sanitized["provider"] == "openai"
    assert sanitized["public_endpoint"] == "https://api.example.com"
    assert "••••" in sanitized["api_key"]
    assert "••••" in sanitized["bearer_token"]
    assert "••••" in sanitized["client_secret"]
    assert "••••" in sanitized["nested"]["password"]

def test_redact_sensitive_dict():
    data = {
        "username": "admin",
        "api_key": "raw_secret_value",
        "auth_token": "token123",
        "details": [
            {"password": "secret", "user": "alice"}
        ]
    }
    redacted = CredentialStore.redact_sensitive_dict(data)
    assert redacted["username"] == "admin"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["auth_token"] == "[REDACTED]"
    assert redacted["details"][0]["password"] == "[REDACTED]"
    assert redacted["details"][0]["user"] == "alice"

def test_token_encode_decode():
    raw = "super_secret_mcp_key_123"
    encoded = CredentialStore.encode_secure_token(raw)
    assert encoded != raw
    decoded = CredentialStore.decode_secure_token(encoded)
    assert decoded == raw
