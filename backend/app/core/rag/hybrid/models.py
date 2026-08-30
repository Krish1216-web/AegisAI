import uuid
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from app.schemas.rag import Citation

class HybridRetrievedItem(BaseModel):
    document_id: Optional[uuid.UUID] = None
    chunk_id: Optional[uuid.UUID] = None
    node_id: Optional[uuid.UUID] = None
    content: str = ""
    source_type: str = "document" # "document" | "graph_node" | "hybrid"
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    vector_score: float = Field(default=0.0, ge=0.0, le=1.0)
    graph_score: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata_score: float = Field(default=0.0, ge=0.0, le=1.0)
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    document_name: Optional[str] = None
    entity_name: Optional[str] = None
    entity_type: Optional[str] = None
    path_info: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class HybridFusionConfig(BaseModel):
    vector_weight: float = 0.60
    graph_weight: float = 0.30
    metadata_weight: float = 0.10
    min_score_threshold: float = 0.15
    max_chunks: int = 8
    max_graph_nodes: int = 10
    max_context_chars: int = 8000

class HybridRAGResult(BaseModel):
    query: str
    answer: str
    retrieved_chunks: List[HybridRetrievedItem] = Field(default_factory=list)
    graph_entities: List[Dict[str, Any]] = Field(default_factory=list)
    graph_relationships: List[Dict[str, Any]] = Field(default_factory=list)
    graph_context: str = ""
    document_evidence: str = ""
    combined_context: str = ""
    citations: List[Citation] = Field(default_factory=list)
    graph_citations: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    conflict_detected: bool = False
    conflict_summary: Optional[str] = None
    retrieval_metrics: Dict[str, Any] = Field(default_factory=dict)
