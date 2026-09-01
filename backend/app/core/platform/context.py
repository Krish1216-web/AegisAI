import uuid
import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from app.core.platform.security import SecurityContext, TrustLevel
from app.core.platform.provenance import ProvenanceItem, ProvenanceTracker
from app.core.mcp.security import CredentialStore

class PlatformContext(BaseModel):
    """
    Typed Phase 8 Execution Context.
    Encapsulates identity, tenant boundaries, credentials redaction, telemetry,
    provenance tracker, and intermediate computation states.
    """
    request_id: str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")
    correlation_id: str = Field(default_factory=lambda: f"corr_{uuid.uuid4().hex[:12]}")
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    session_id: Optional[str] = None
    execution_id: Optional[uuid.UUID] = None
    workflow_id: Optional[uuid.UUID] = None
    workflow_version: Optional[int] = None
    agent_id: Optional[str] = None
    security_context: SecurityContext
    input_data: Dict[str, Any] = Field(default_factory=dict)
    intermediate_results: Dict[str, Any] = Field(default_factory=dict)
    provenance: List[ProvenanceItem] = Field(default_factory=list)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_provenance(self, item: ProvenanceItem) -> None:
        """Attaches provenance ensuring tenant match."""
        if item.workspace_id != self.workspace_id:
            raise PermissionError("Cross-tenant provenance attachment is forbidden.")
        self.provenance.append(item)

    def add_error(self, code: str, message: str, node_key: Optional[str] = None) -> None:
        """Appends a sanitized error."""
        clean_msg = CredentialStore.redact_sensitive_str(message)
        self.errors.append({
            "code": code,
            "message": clean_msg,
            "node_key": node_key,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })

    def add_warning(self, warning: str) -> None:
        """Appends a sanitized warning message."""
        self.warnings.append(CredentialStore.redact_sensitive_str(warning))

    def set_result(self, key: str, value: Any) -> None:
        """Stores intermediate computation result."""
        self.intermediate_results[key] = value

    def get_safe_dict(self) -> Dict[str, Any]:
        """Returns safe representation with redacted inputs and errors."""
        return {
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "user_id": str(self.user_id),
            "workspace_id": str(self.workspace_id),
            "session_id": self.session_id,
            "execution_id": str(self.execution_id) if self.execution_id else None,
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "agent_id": self.agent_id,
            "input_data": CredentialStore.redact_sensitive_dict(self.input_data),
            "intermediate_results": CredentialStore.redact_sensitive_dict(self.intermediate_results),
            "provenance_count": len(self.provenance),
            "errors": self.errors,
            "warnings": self.warnings,
            "created_at": self.created_at.isoformat()
        }
