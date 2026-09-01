from typing import Dict, Any, List
from pydantic import BaseModel, Field
from app.core.platform.capability import CapabilityType

class PlatformSettings(BaseModel):
    """
    Configuration and governance settings for Phase 8 platform capabilities.
    """
    max_execution_timeout_seconds: int = Field(default=600, ge=10, le=3600)
    max_context_tokens: int = Field(default=32000, ge=1000, le=128000)
    max_concurrency_limit: int = Field(default=10, ge=1, le=50)
    max_provenance_items: int = Field(default=100, ge=5, le=500)
    max_subworkflow_depth: int = Field(default=3, ge=1, le=5)
    
    # Feature Flags
    feature_flags: Dict[str, bool] = Field(default_factory=lambda: {
        "enable_phase8_intelligence": True,
        "enable_advanced_reasoning": True,
        "enable_cross_capability_provenance": True,
        "enable_realtime_telemetry": True,
        "strict_tenant_isolation": True
    })
    
    enabled_capabilities: List[CapabilityType] = Field(default_factory=lambda: [
        CapabilityType.AGENT,
        CapabilityType.RAG,
        CapabilityType.KNOWLEDGE_GRAPH,
        CapabilityType.MEMORY,
        CapabilityType.MCP,
        CapabilityType.WORKFLOW,
        CapabilityType.INTELLIGENCE,
        CapabilityType.REASONING
    ])
    
    observability_level: str = "info"

def get_platform_settings() -> PlatformSettings:
    """Returns singleton platform settings instance."""
    return PlatformSettings()
