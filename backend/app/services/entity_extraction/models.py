import uuid
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator

from app.models.knowledge_graph import NodeType, RelationshipType

class ExtractedEntity(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    entity_type: str = Field(default=NodeType.PROJECT.value)
    description: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_text: Optional[str] = None
    start_offset: Optional[int] = Field(default=None, ge=0)
    end_offset: Optional[int] = Field(default=None, ge=0)
    document_id: Optional[uuid.UUID] = None
    chunk_id: Optional[uuid.UUID] = None
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        valid_types = {t.value for t in NodeType}
        if v not in valid_types:
            # Default to PROJECT if unrecognized
            return NodeType.PROJECT.value
        return v

class ExtractedRelationship(BaseModel):
    source_entity_name: str = Field(..., min_length=1, max_length=255)
    target_entity_name: str = Field(..., min_length=1, max_length=255)
    relationship_type: str = Field(default=RelationshipType.RELATED_TO.value)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_text: Optional[str] = None
    document_id: Optional[uuid.UUID] = None
    chunk_id: Optional[uuid.UUID] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("relationship_type")
    @classmethod
    def validate_relationship_type(cls, v: str) -> str:
        valid_rels = {r.value for r in RelationshipType}
        if v not in valid_rels:
            return RelationshipType.RELATED_TO.value
        return v

class ExtractionResult(BaseModel):
    entities: List[ExtractedEntity] = Field(default_factory=list)
    relationships: List[ExtractedRelationship] = Field(default_factory=list)
    document_id: Optional[uuid.UUID] = None
    chunk_id: Optional[uuid.UUID] = None
    extraction_time: float = 0.0
    provider: str = "rule_based"

class ExtractionConfig(BaseModel):
    provider: str = "rule_based"
    max_entities_per_chunk: int = 50
    max_relationships_per_chunk: int = 100
    confidence_threshold: float = 0.3
