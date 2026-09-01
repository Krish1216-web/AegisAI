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
from app.core.platform.knowledge_bridge import KnowledgeContextBridge
from app.core.platform.knowledge_adapters import (
    RAGCapabilityAdapter,
    HybridRAGCapabilityAdapter,
    GraphCapabilityAdapter
)
from app.core.platform.mcp_bridge import MCPContextBridge
from app.core.platform.mcp_adapters import (
    MCPToolCapabilityAdapter,
    MCPResourceCapabilityAdapter,
    MCPPromptCapabilityAdapter,
    MCPCapabilityAdapter
)

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
    "AgentCapabilityAdapter",
    "KnowledgeContextBridge",
    "RAGCapabilityAdapter",
    "HybridRAGCapabilityAdapter",
    "GraphCapabilityAdapter",
    "MCPContextBridge",
    "MCPToolCapabilityAdapter",
    "MCPResourceCapabilityAdapter",
    "MCPPromptCapabilityAdapter",
    "MCPCapabilityAdapter"
]
