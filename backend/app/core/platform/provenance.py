import uuid
import datetime
import enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class ProvenanceSourceType(str, enum.Enum):
    DOCUMENT = "document"
    DOCUMENT_CHUNK = "document_chunk"
    GRAPH_NODE = "graph_node"
    GRAPH_EDGE = "graph_edge"
    MEMORY_FACT = "memory_fact"
    MCP_TOOL = "mcp_tool"
    MCP_RESOURCE = "mcp_resource"
    MCP_PROMPT = "mcp_prompt"
    WORKFLOW_NODE = "workflow_node"
    AGENT_REASONING = "agent_reasoning"
    EXTERNAL_RESEARCH = "external_research"

class ProvenanceTrustLevel(str, enum.Enum):
    TRUSTED_INTERNAL = "trusted_internal"
    VERIFIED_RAG = "verified_rag"
    VERIFIED_GRAPH = "verified_graph"
    VERIFIED_MEMORY = "verified_memory"
    UNTRUSTED_MCP = "untrusted_mcp"
    UNTRUSTED_EXTERNAL = "untrusted_external"
    SYNTHETIC = "synthetic"

class ProvenanceItem(BaseModel):
    """
    Unified evidence provenance citation record.
    Represents citations originating from RAG, Graph, Memory, MCP, Workflows, or Agents.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: ProvenanceSourceType
    source_id: str
    uri: Optional[str] = None
    title: Optional[str] = None
    snippet: Optional[str] = None
    trust_level: ProvenanceTrustLevel = ProvenanceTrustLevel.TRUSTED_INTERNAL
    confidence: float = 1.0
    workspace_id: uuid.UUID
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def is_untrusted(self) -> bool:
        """Returns True if the source is from external/untrusted origins."""
        return self.trust_level in [
            ProvenanceTrustLevel.UNTRUSTED_MCP,
            ProvenanceTrustLevel.UNTRUSTED_EXTERNAL
        ]

class ProvenanceTracker:
    """
    Tracks and deduplicates citations and evidence items in an execution context.
    """
    def __init__(self, workspace_id: uuid.UUID):
        self.workspace_id = workspace_id
        self._items: List[ProvenanceItem] = []
        self._seen_ids = set()

    def add(self, item: ProvenanceItem) -> None:
        """Adds a provenance item if tenant-isolated and unique."""
        if item.workspace_id != self.workspace_id:
            raise PermissionError("Cannot attach provenance item from a different workspace.")
        
        dedup_key = f"{item.source_type.value}:{item.source_id}"
        if dedup_key not in self._seen_ids:
            self._seen_ids.add(dedup_key)
            self._items.append(item)

    def get_items(self) -> List[ProvenanceItem]:
        return list(self._items)

    def has_untrusted_content(self) -> bool:
        return any(item.is_untrusted() for item in self._items)
