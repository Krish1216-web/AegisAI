import uuid
import pytest
from app.core.mcp.security import CredentialStore

def test_credential_redaction():
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 and API_KEY=sk-1234567890abcdef"
    redacted = CredentialStore.redact_sensitive_str(text)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted
    assert "[REDACTED]" in redacted
