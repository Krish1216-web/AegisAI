import uuid
import json
import datetime
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field, field_validator

from app.models.knowledge_graph import NodeType, RelationshipType

MAX_METADATA_SIZE_BYTES = 65536

def validate_meta_size(value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if value is not None:
        try:
            serialized = json.dumps(value)
            if len(serialized.encode("utf-8")) > MAX_METADATA_SIZE_BYTES:
                raise ValueError(f"Metadata/properties payload exceeds maximum allowed size of {MAX_METADATA_SIZE_BYTES} bytes.")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid metadata format: {e}")
    return value

class NodeCreate(BaseModel):
    node_type: str
    name: str = Field(..., min_length=1, max_length=255)
    external_id: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("node_type")
    @classmethod
    def validate_node_type(cls, v: str) -> str:
        valid_types = {t.value for t in NodeType}
        if v not in valid_types:
            raise ValueError(f"Invalid node_type '{v}'. Must be one of: {sorted(list(valid_types))}")
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        return validate_meta_size(v)

class NodeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        return validate_meta_size(v)

class NodeResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    node_type: str
    external_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(None, validation_alias="meta_data")
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True
        populate_by_name = True

class EdgeCreate(BaseModel):
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    relationship_type: str
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    properties: Optional[Dict[str, Any]] = None

    @field_validator("relationship_type")
    @classmethod
    def validate_relationship_type(cls, v: str) -> str:
        valid_rels = {r.value for r in RelationshipType}
        if v not in valid_rels:
            raise ValueError(f"Invalid relationship_type '{v}'. Must be one of: {sorted(list(valid_rels))}")
        return v

    @field_validator("properties")
    @classmethod
    def validate_properties(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        return validate_meta_size(v)

class EdgeResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    relationship_type: str
    confidence: float
    properties: Optional[Dict[str, Any]] = Field(None, validation_alias="meta_data")
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True
        populate_by_name = True

class NeighborResponse(BaseModel):
    node: NodeResponse
    relationship_type: str
    direction: Literal["outgoing", "incoming"]
    confidence: float
    edge_id: uuid.UUID

class GraphTraversalRequest(BaseModel):
    start_node_ids: List[uuid.UUID] = Field(..., min_length=1)
    max_depth: int = Field(3, ge=1, le=5)
    relationship_types: Optional[List[str]] = None
    node_types: Optional[List[str]] = None
    limit: int = Field(100, ge=1, le=500)

    @field_validator("relationship_types")
    @classmethod
    def validate_rels(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            valid_rels = {r.value for r in RelationshipType}
            for rel in v:
                if rel not in valid_rels:
                    raise ValueError(f"Invalid relationship_type '{rel}' in filter.")
        return v

    @field_validator("node_types")
    @classmethod
    def validate_nodes(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            valid_types = {t.value for t in NodeType}
            for nt in v:
                if nt not in valid_types:
                    raise ValueError(f"Invalid node_type '{nt}' in filter.")
        return v

class GraphTraversalResponse(BaseModel):
    nodes: List[NodeResponse]
    edges: List[EdgeResponse]
    depth_reached: int
    total_nodes: int
    total_edges: int

class GraphContextResponse(BaseModel):
    entities: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    formatted_context: str

# ---------------------------------------------------------
# Phase 5.1: Graph Intelligence Schemas
# ---------------------------------------------------------

class RelatedEntityItem(BaseModel):
    node_id: uuid.UUID
    node_type: str
    name: str
    description: Optional[str] = None
    distance: int
    relevance_score: float
    relationship_path: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

class RelatedEntitiesResponse(BaseModel):
    node_id: uuid.UUID
    depth: int
    total_related: int
    related_entities: List[RelatedEntityItem]

class GraphPathStep(BaseModel):
    from_node_id: uuid.UUID
    from_node_name: str
    to_node_id: uuid.UUID
    to_node_name: str
    relationship_type: str
    direction: Literal["outgoing", "incoming"]
    confidence: float

class GraphPathResponse(BaseModel):
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    path_found: bool
    distance: int
    steps: List[GraphPathStep]
    nodes: List[NodeResponse]

class PathSearchRequest(BaseModel):
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    max_depth: int = Field(5, ge=1, le=10)
    allowed_relationship_types: Optional[List[str]] = None

class RelationshipDetail(BaseModel):
    relationship_type: str
    direction: Literal["outgoing", "incoming", "bidirectional"]
    confidence: float
    distance: int
    via_nodes: List[str] = Field(default_factory=list)

class RelationshipAnalysisRequest(BaseModel):
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    max_depth: int = Field(3, ge=1, le=5)

class RelationshipAnalysisResponse(BaseModel):
    source_node: NodeResponse
    target_node: NodeResponse
    are_connected: bool
    min_distance: Optional[int] = None
    direct_relationships: List[RelationshipDetail] = Field(default_factory=list)
    indirect_relationships: List[RelationshipDetail] = Field(default_factory=list)
    summary: str

class GraphIntelligenceContextRequest(BaseModel):
    entity_names: Optional[List[str]] = None
    node_ids: Optional[List[uuid.UUID]] = None
    depth: int = Field(2, ge=1, le=4)
    max_entities: int = Field(20, ge=1, le=100)

# ---------------------------------------------------------
# Phase 5.8: Graph Search & Analytics Schemas
# ---------------------------------------------------------

class GraphAnalyticsOverview(BaseModel):
    total_nodes: int
    total_edges: int
    nodes_by_type: Dict[str, int] = Field(default_factory=dict)
    edges_by_type: Dict[str, int] = Field(default_factory=dict)
    average_degree: float = 0.0
    max_degree: int = 0
    isolated_nodes_count: int = 0
    connected_nodes_count: int = 0
    graph_density: float = 0.0
    average_confidence: float = 0.0
    provenance_distribution: Dict[str, int] = Field(default_factory=dict)

class GraphHealthReport(BaseModel):
    status: Literal["HEALTHY", "WARNING", "CRITICAL"]
    orphan_rate: float
    low_confidence_edges_count: int
    conflicts_count: int
    unresolved_provenance_count: int
    diagnostic_messages: List[str] = Field(default_factory=list)

class TopConnectedEntity(BaseModel):
    node_id: uuid.UUID
    name: str
    node_type: str
    degree: int
    in_degree: int
    out_degree: int

class DuplicateCandidate(BaseModel):
    source_node_id: uuid.UUID
    source_name: str
    target_node_id: uuid.UUID
    target_name: str
    entity_type: str
    similarity_score: float
    reason: str

class SearchResultItem(BaseModel):
    node: NodeResponse
    relevance_score: float
    match_type: Literal["exact", "prefix", "partial", "description", "fuzzy"]
    degree: int = 0

class AdvancedSearchRequest(BaseModel):
    query: Optional[str] = None
    node_type: Optional[str] = None
    relationship_type: Optional[str] = None
    min_confidence: float = Field(0.0, ge=0.0, le=1.0)
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)

class AdvancedSearchResponse(BaseModel):
    results: List[SearchResultItem]
    total_matched: int
    search_latency_ms: float

