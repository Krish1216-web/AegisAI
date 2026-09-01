import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.core.platform.capability import CapabilityMetadata, CapabilityType
from app.core.platform.lifecycle import LifecycleState
from app.core.platform.provenance import ProvenanceItem

class PlatformStatusResponse(BaseModel):
    version: str = "8.1.0"
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
