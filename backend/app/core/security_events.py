import uuid
import datetime
import enum
import hashlib
import json
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from app.core.mcp.security import CredentialStore

class SecurityEventType(str, enum.Enum):
    # Authentication & Session Events
    AUTH_LOGIN_SUCCESS = "AUTH_LOGIN_SUCCESS"
    AUTH_LOGIN_FAILED = "AUTH_LOGIN_FAILED"
    AUTH_REGISTER = "AUTH_REGISTER"
    AUTH_TOKEN_ROTATED = "AUTH_TOKEN_ROTATED"
    AUTH_LOGOUT = "AUTH_LOGOUT"
    AUTH_REFRESH_REPLAY = "AUTH_REFRESH_REPLAY"
    ACCOUNT_SUSPENDED = "ACCOUNT_SUSPENDED"
    ACCOUNT_DELETED_ACCESS_ATTEMPT = "ACCOUNT_DELETED_ACCESS_ATTEMPT"

    # Authorization & Tenant Boundary Events
    AUTHZ_DENIED = "AUTHZ_DENIED"
    TENANT_BOUNDARY_VIOLATION = "TENANT_BOUNDARY_VIOLATION"
    IDOR_ATTEMPT = "IDOR_ATTEMPT"
    BOLA_ATTEMPT = "BOLA_ATTEMPT"

    # Privilege & Governance Events
    ROLE_CHANGED = "ROLE_CHANGED"
    PERMISSION_CHANGED = "PERMISSION_CHANGED"
    OWNERSHIP_TRANSFERRED = "OWNERSHIP_TRANSFERRED"

    # Administrative Actions
    ADMIN_ACTION = "ADMIN_ACTION"
    ADMIN_ACCESS = "ADMIN_ACCESS"
    ADMIN_SUSPENSION_ACTION = "ADMIN_SUSPENSION_ACTION"

    # Rate Limiting & Abuse
    RATE_LIMIT_TRIGGERED = "RATE_LIMIT_TRIGGERED"
    RATE_LIMIT_ABUSE = "RATE_LIMIT_ABUSE"

    # Outbound Network & Filesystem Security
    SSRF_BLOCKED = "SSRF_BLOCKED"
    PATH_TRAVERSAL_BLOCKED = "PATH_TRAVERSAL_BLOCKED"

    # AI & Prompt Injection Security
    PROMPT_INJECTION_DETECTED = "PROMPT_INJECTION_DETECTED"
    PROMPT_INJECTION_BLOCKED = "PROMPT_INJECTION_BLOCKED"

    # MCP Security
    MCP_SECURITY_VIOLATION = "MCP_SECURITY_VIOLATION"
    MCP_RESTRICTED_TOOL_ATTEMPT = "MCP_RESTRICTED_TOOL_ATTEMPT"
    MCP_CONFIRMATION_FAILED = "MCP_CONFIRMATION_FAILED"

    # Document & Workflow Security
    DOCUMENT_SECURITY_VIOLATION = "DOCUMENT_SECURITY_VIOLATION"
    WORKFLOW_SECURITY_VIOLATION = "WORKFLOW_SECURITY_VIOLATION"

    # Execution Lifecycle Failures
    EXECUTION_CANCELLED = "EXECUTION_CANCELLED"
    EXECUTION_TIMEOUT = "EXECUTION_TIMEOUT"
    EXECUTION_FAILURE = "EXECUTION_FAILURE"

    # Secrets, Suspicious & System Security
    SECRET_REDACTION_EVENT = "SECRET_REDACTION_EVENT"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
    SECURITY_ALERT = "SECURITY_ALERT"
    SECURITY_CONFIGURATION_CHANGED = "SECURITY_CONFIGURATION_CHANGED"

class SecuritySeverity(str, enum.Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

DEFAULT_SEVERITY_MAP: Dict[SecurityEventType, SecuritySeverity] = {
    SecurityEventType.AUTH_LOGIN_SUCCESS: SecuritySeverity.INFO,
    SecurityEventType.AUTH_LOGIN_FAILED: SecuritySeverity.MEDIUM,
    SecurityEventType.AUTH_REGISTER: SecuritySeverity.INFO,
    SecurityEventType.AUTH_TOKEN_ROTATED: SecuritySeverity.INFO,
    SecurityEventType.AUTH_LOGOUT: SecuritySeverity.INFO,
    SecurityEventType.AUTH_REFRESH_REPLAY: SecuritySeverity.CRITICAL,
    SecurityEventType.ACCOUNT_SUSPENDED: SecuritySeverity.MEDIUM,
    SecurityEventType.ACCOUNT_DELETED_ACCESS_ATTEMPT: SecuritySeverity.HIGH,
    SecurityEventType.AUTHZ_DENIED: SecuritySeverity.MEDIUM,
    SecurityEventType.TENANT_BOUNDARY_VIOLATION: SecuritySeverity.HIGH,
    SecurityEventType.IDOR_ATTEMPT: SecuritySeverity.HIGH,
    SecurityEventType.BOLA_ATTEMPT: SecuritySeverity.HIGH,
    SecurityEventType.ROLE_CHANGED: SecuritySeverity.MEDIUM,
    SecurityEventType.PERMISSION_CHANGED: SecuritySeverity.MEDIUM,
    SecurityEventType.OWNERSHIP_TRANSFERRED: SecuritySeverity.HIGH,
    SecurityEventType.ADMIN_ACTION: SecuritySeverity.MEDIUM,
    SecurityEventType.ADMIN_ACCESS: SecuritySeverity.INFO,
    SecurityEventType.ADMIN_SUSPENSION_ACTION: SecuritySeverity.HIGH,
    SecurityEventType.RATE_LIMIT_TRIGGERED: SecuritySeverity.LOW,
    SecurityEventType.RATE_LIMIT_ABUSE: SecuritySeverity.MEDIUM,
    SecurityEventType.SSRF_BLOCKED: SecuritySeverity.HIGH,
    SecurityEventType.PATH_TRAVERSAL_BLOCKED: SecuritySeverity.HIGH,
    SecurityEventType.PROMPT_INJECTION_DETECTED: SecuritySeverity.MEDIUM,
    SecurityEventType.PROMPT_INJECTION_BLOCKED: SecuritySeverity.HIGH,
    SecurityEventType.MCP_SECURITY_VIOLATION: SecuritySeverity.HIGH,
    SecurityEventType.MCP_RESTRICTED_TOOL_ATTEMPT: SecuritySeverity.HIGH,
    SecurityEventType.MCP_CONFIRMATION_FAILED: SecuritySeverity.MEDIUM,
    SecurityEventType.DOCUMENT_SECURITY_VIOLATION: SecuritySeverity.MEDIUM,
    SecurityEventType.WORKFLOW_SECURITY_VIOLATION: SecuritySeverity.HIGH,
    SecurityEventType.EXECUTION_CANCELLED: SecuritySeverity.LOW,
    SecurityEventType.EXECUTION_TIMEOUT: SecuritySeverity.MEDIUM,
    SecurityEventType.EXECUTION_FAILURE: SecuritySeverity.MEDIUM,
    SecurityEventType.SECRET_REDACTION_EVENT: SecuritySeverity.LOW,
    SecurityEventType.SUSPICIOUS_ACTIVITY: SecuritySeverity.HIGH,
    SecurityEventType.SECURITY_ALERT: SecuritySeverity.HIGH,
    SecurityEventType.SECURITY_CONFIGURATION_CHANGED: SecuritySeverity.HIGH
}

class SecurityEventRecord(BaseModel):
    """
    Canonical, tamper-evident security event data structure with recursive secret redaction.
    """
    event_id: str = Field(default_factory=lambda: f"sec_{uuid.uuid4().hex[:12]}")
    event_type: SecurityEventType
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    severity: SecuritySeverity = SecuritySeverity.INFO
    actor_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    team_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    execution_id: Optional[str] = None
    source_component: str
    action: str
    outcome: str = "SUCCESS" # e.g. SUCCESS, DENIED, BLOCKED, DETECTED, FAILURE
    reason: Optional[str] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    security_metadata: Dict[str, Any] = Field(default_factory=dict)
    sanitized_details: Dict[str, Any] = Field(default_factory=dict)
    event_hash: Optional[str] = None
    previous_hash: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        # Default severity lookup if not explicitly overridden
        if self.severity == SecuritySeverity.INFO and self.event_type in DEFAULT_SEVERITY_MAP:
            self.severity = DEFAULT_SEVERITY_MAP[self.event_type]

        # Recursively redact secrets and PII from metadata and details
        self.security_metadata = CredentialStore.redact_sensitive_dict(self.security_metadata)
        self.sanitized_details = CredentialStore.redact_sensitive_dict(self.sanitized_details)
        if self.reason:
            self.reason = CredentialStore.redact_sensitive_str(self.reason)

    def canonical_bytes(self) -> bytes:
        """Returns deterministic canonical JSON representation of event attributes."""
        payload = {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "actor_id": str(self.actor_id) if self.actor_id else None,
            "workspace_id": str(self.workspace_id) if self.workspace_id else None,
            "team_id": str(self.team_id) if self.team_id else None,
            "project_id": str(self.project_id) if self.project_id else None,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "execution_id": self.execution_id,
            "source_component": self.source_component,
            "action": self.action,
            "outcome": self.outcome,
            "reason": self.reason,
            "source_ip": self.source_ip,
            "security_metadata": self.security_metadata,
            "sanitized_details": self.sanitized_details,
            "previous_hash": self.previous_hash or "GENESIS_HASH"
        }
        return json.dumps(payload, sort_keys=True, default=str).encode("utf-8")

    def compute_hash(self, previous_hash: Optional[str] = None) -> str:
        """Computes SHA-256 cryptographic digest for chain tamper-evidence."""
        self.previous_hash = previous_hash or self.previous_hash or "GENESIS_HASH"
        hasher = hashlib.sha256()
        hasher.update(self.canonical_bytes())
        self.event_hash = hasher.hexdigest()
        return self.event_hash
