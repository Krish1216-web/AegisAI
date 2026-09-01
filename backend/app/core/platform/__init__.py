"""
Phase 8 Advanced Platform Architecture Package.
"""
from app.core.platform.security import TrustLevel, SecurityContext
from app.core.platform.provenance import (
    ProvenanceSourceType,
    ProvenanceTrustLevel,
    ProvenanceItem,
    ProvenanceTracker
)
from app.core.platform.context import PlatformContext
from app.core.platform.lifecycle import (
    LifecycleState,
    LifecycleEvent,
    InvalidStateTransitionError,
    LifecycleStateMachine
)
from app.core.platform.events import (
    PlatformEventType,
    PlatformEvent,
    PlatformEventDispatcher
)
from app.core.platform.capability import (
    CapabilityType,
    CapabilityMetadata,
    PlatformCapability,
    CapabilityRegistry,
    platform_capability_registry
)
from app.core.platform.config import PlatformSettings, get_platform_settings
from app.core.platform.agent_bridge import AgentContextBridge
from app.core.platform.agent_adapter import AgentCapabilityAdapter

__all__ = [
    "TrustLevel",
    "SecurityContext",
    "ProvenanceSourceType",
    "ProvenanceTrustLevel",
    "ProvenanceItem",
    "ProvenanceTracker",
    "PlatformContext",
    "LifecycleState",
    "LifecycleEvent",
    "InvalidStateTransitionError",
    "LifecycleStateMachine",
    "PlatformEventType",
    "PlatformEvent",
    "PlatformEventDispatcher",
    "CapabilityType",
    "CapabilityMetadata",
    "PlatformCapability",
    "CapabilityRegistry",
    "platform_capability_registry",
    "PlatformSettings",
    "get_platform_settings",
    "AgentContextBridge",
    "AgentCapabilityAdapter"
]
