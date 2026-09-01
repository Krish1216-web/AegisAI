import uuid
import enum
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Set
from pydantic import BaseModel, Field

class CapabilityType(str, enum.Enum):
    AGENT = "agent"
    RAG = "rag"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    MEMORY = "memory"
    MCP = "mcp"
    WORKFLOW = "workflow"
    EXTERNAL_SERVICE = "external_service"
    INTELLIGENCE = "intelligence"
    REASONING = "reasoning"

class CapabilityMetadata(BaseModel):
    """
    Metadata definition for registered platform capabilities.
    """
    capability_id: str
    capability_type: CapabilityType
    name: str
    description: str
    version: str = "1.0.0"
    enabled: bool = True
    workspace_scope: Optional[uuid.UUID] = None  # None indicates system-wide capability
    required_permissions: Set[str] = Field(default_factory=set)
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PlatformCapability(ABC):
    """
    Abstract Base Class for Phase 8 platform capabilities.
    """
    def __init__(self, metadata: CapabilityMetadata):
        self.metadata = metadata

    @property
    def capability_id(self) -> str:
        return self.metadata.capability_id

    @property
    def capability_type(self) -> CapabilityType:
        return self.metadata.capability_type

    def is_accessible_by(self, workspace_id: uuid.UUID, user_role: str, user_permissions: Set[str]) -> bool:
        """Enforces tenant isolation and RBAC."""
        # Workspace scoping check
        if self.metadata.workspace_scope is not None and self.metadata.workspace_scope != workspace_id:
            return False
        
        # Enabled check
        if not self.metadata.enabled:
            return False

        # Admin bypass
        if user_role == "admin":
            return True

        # Required permissions check
        if self.metadata.required_permissions:
            return self.metadata.required_permissions.issubset(user_permissions)

        return True

class CapabilityRegistry:
    """
    Thread-safe registry of active platform capabilities.
    """
    def __init__(self):
        self._capabilities: Dict[str, PlatformCapability] = {}

    def register(self, capability: PlatformCapability) -> None:
        self._capabilities[capability.capability_id] = capability

    def unregister(self, capability_id: str) -> None:
        self._capabilities.pop(capability_id, None)

    def get(self, capability_id: str) -> Optional[PlatformCapability]:
        return self._capabilities.get(capability_id)

    def list_all(self) -> List[PlatformCapability]:
        """Returns all registered capability objects."""
        return list(self._capabilities.values())

    def list_available(
        self,
        workspace_id: uuid.UUID,
        user_role: str = "viewer",
        user_permissions: Optional[Set[str]] = None,
        capability_type: Optional[CapabilityType] = None
    ) -> List[CapabilityMetadata]:
        """Lists capabilities available to caller under tenant and RBAC constraints."""
        perms = user_permissions or set()
        matched = []
        for cap in self._capabilities.values():
            if capability_type and cap.capability_type != capability_type:
                continue
            if cap.is_accessible_by(workspace_id, user_role, perms):
                matched.append(cap.metadata)
        
        # Deterministic sorting by name
        matched.sort(key=lambda x: (x.capability_type.value, x.name))
        return matched

# Global Platform Capability Registry instance
platform_capability_registry = CapabilityRegistry()
