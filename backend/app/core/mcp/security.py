import os
import re
import base64
import hashlib
from typing import Dict, Any, Optional

SENSITIVE_KEY_PATTERNS = re.compile(
    r"(api[_-]?key|secret|token|password|auth|bearer|credential|private[_-]?key)",
    re.IGNORECASE
)

class CredentialStore:
    """
    Interface for secure credential storage, masking, and redaction.
    """
    @staticmethod
    def mask_credential(secret: Optional[str]) -> str:
        """Masks a secret string preserving only prefix/suffix for identification."""
        if not secret:
            return ""
        if len(secret) <= 6:
            return "••••••••"
        prefix = secret[:3]
        suffix = secret[-3:]
        return f"{prefix}••••{suffix}"

    @staticmethod
    def sanitize_auth_config(auth_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Returns a sanitized copy of auth_config with all sensitive fields masked.
        Safe for API responses and logs.
        """
        if not auth_config:
            return {}
        sanitized = {}
        for k, v in auth_config.items():
            if isinstance(v, str) and SENSITIVE_KEY_PATTERNS.search(k):
                sanitized[k] = CredentialStore.mask_credential(v)
            elif isinstance(v, dict):
                sanitized[k] = CredentialStore.sanitize_auth_config(v)
            else:
                sanitized[k] = v
        return sanitized

    @staticmethod
    def redact_sensitive_str(text: Optional[str]) -> str:
        """Sanitizes sensitive values in strings (e.g. passwords, tokens, API keys, database URLs, private keys)."""
        if not text:
            return ""
        s = str(text)
        # Redact private keys
        s = re.sub(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----", "[REDACTED_PRIVATE_KEY]", s)
        # Redact Bearer tokens
        s = re.sub(r"(Bearer\s+)([^\s,;]+)", r"\1[REDACTED]", s, flags=re.IGNORECASE)
        # Redact JWT tokens
        s = re.sub(r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]+", "[REDACTED]", s)
        # Redact database and Redis connection URIs with embedded credentials
        s = re.sub(r"(?i)(postgresql|postgres|sqlite|mysql|mongodb|redis|amqp|smtp):\/\/([^@\n\s]+)@([^\n\s/]+)", r"\1://[REDACTED_CREDENTIALS]@\3", s)
        # Redact common provider API key patterns (OpenAI sk-, Google AIza-, GitHub ghp-, Slack xoxb-)
        s = re.sub(r"(?i)\b(sk-[a-zA-Z0-9_\-]{16,})\b", "[REDACTED_API_KEY]", s)
        s = re.sub(r"\bAIza[0-9A-Za-z-_]{35}\b", "[REDACTED_API_KEY]", s)
        s = re.sub(r"\bghp_[a-zA-Z0-9]{36}\b", "[REDACTED_API_KEY]", s)
        s = re.sub(r"\bxoxb-[0-9]{11,13}-[0-9]{11,13}-[a-zA-Z0-9]{24}\b", "[REDACTED_API_KEY]", s)
        # Redact explicit secret/token/password/key assignments
        s = re.sub(
            r"(api[_-]?key|secret|token|password|auth|credential|private[_-]?key)\s*[:=]\s*([^\s,;]+)",
            r"\1=[REDACTED]",
            s,
            flags=re.IGNORECASE
        )
        return s

    @staticmethod
    def redact_sensitive_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redacts sensitive keys and values from any dictionary."""
        if not isinstance(data, dict):
            return data
        redacted = {}
        for k, v in data.items():
            if SENSITIVE_KEY_PATTERNS.search(str(k)):
                redacted[k] = "[REDACTED]"
            elif isinstance(v, str):
                redacted[k] = CredentialStore.redact_sensitive_str(v)
            elif isinstance(v, dict):
                redacted[k] = CredentialStore.redact_sensitive_dict(v)
            elif isinstance(v, list):
                redacted[k] = [
                    CredentialStore.redact_sensitive_dict(item) if isinstance(item, dict) else (
                        CredentialStore.redact_sensitive_str(item) if isinstance(item, str) else item
                    )
                    for item in v
                ]
            else:
                redacted[k] = v
        return redacted

    @staticmethod
    def encode_secure_token(raw_token: str) -> str:
        """Securely prepares token for storage."""
        if not raw_token:
            return ""
        # Base64 obscured token representation for Phase 6.1 pluggable storage
        return base64.b64encode(raw_token.encode("utf-8")).decode("utf-8")

    @staticmethod
    def decode_secure_token(encoded: str) -> str:
        """Decodes stored token representation."""
        if not encoded:
            return ""
        try:
            return base64.b64decode(encoded.encode("utf-8")).decode("utf-8")
        except Exception:
            return encoded
