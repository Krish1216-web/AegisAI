import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.core.platform.lifecycle import LifecycleState
from app.core.platform.provenance import ProvenanceItem
from app.core.mcp.security import CredentialStore

class PlatformExecutionResult(BaseModel):
    """
    Strongly typed execution output record from the Platform Execution Engine.
    """
    execution_id: str
    capability_id: str
    status: LifecycleState
    output: Dict[str, Any] = Field(default_factory=dict)
    provenance: List[ProvenanceItem] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    started_at: datetime.datetime
    completed_at: Optional[datetime.datetime] = None
    duration_ms: float = 0.0
    correlation_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_safe_dict(self) -> Dict[str, Any]:
        """Returns serialized dictionary with secrets recursively redacted."""
        return {
            "execution_id": self.execution_id,
            "capability_id": self.capability_id,
            "status": self.status.value,
            "output": CredentialStore.redact_sensitive_dict(self.output),
            "provenance": [p.dict() for p in self.provenance],
            "warnings": [CredentialStore.redact_sensitive_str(w) for w in self.warnings],
            "errors": [
                {
                    "code": e.get("code", "ERROR"),
                    "message": CredentialStore.redact_sensitive_str(e.get("message", ""))
                }
                for e in self.errors
            ],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": round(self.duration_ms, 2),
            "correlation_id": self.correlation_id,
            "metadata": CredentialStore.redact_sensitive_dict(self.metadata)
        }
