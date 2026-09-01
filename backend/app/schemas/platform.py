import uuid
import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.core.platform.capability import CapabilityMetadata, CapabilityType
from app.core.platform.lifecycle import LifecycleState
from app.core.platform.provenance import ProvenanceItem

class PlatformStatusResponse(BaseModel):
    version: str = "8.2.0"
    phase: str = "Phase 8: Advanced Platform"
    workspace_id: uuid.UUID
    active_capabilities: int
    system_health: str = "HEALTHY"
    feature_flags: Dict[str, bool]
    registered_subsystems: List[str]

class PlatformCapabilityResponse(BaseModel):
    capability: CapabilityMetadata

class PlatformCapabilityListResponse(BaseModel):
    total: int
    items: List[CapabilityMetadata]
    workspace_id: uuid.UUID

class PlatformExecutionRequest(BaseModel):
    capability_id: str
    input_data: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None
    timeout_seconds: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PlatformExecutionResponse(BaseModel):
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

class PlatformExecutionCancelRequest(BaseModel):
    reason: Optional[str] = "User requested cancellation"

class PlatformIntelligenceRequest(BaseModel):
    query: str
    mode: str = "adaptive"
    input_data: Dict[str, Any] = Field(default_factory=dict)
    confidence_threshold: float = 0.60

class PlatformIntelligenceResponse(BaseModel):
    execution_id: str
    query: str
    status: str
    mode: str
    plan: Dict[str, Any] = Field(default_factory=dict)
    decisions: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_evaluation: Dict[str, Any] = Field(default_factory=dict)
    confidence: float
    confidence_level: str
    output: Dict[str, Any] = Field(default_factory=dict)
    provenance: List[Dict[str, Any]] = Field(default_factory=list)
    duration_ms: float = 0.0
    correlation_id: str
