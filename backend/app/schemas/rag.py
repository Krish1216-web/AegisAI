from pydantic import BaseModel, Field
import uuid
from typing import List, Optional

class Citation(BaseModel):
    citation_number: int
    document_id: uuid.UUID
    document_name: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    snippet: str

    class Config:
        from_attributes = True

class RetrievedChunk(BaseModel):
    chunk_id: uuid.UUID = Field(..., validation_alias="id")
    document_id: uuid.UUID
    document_name: str
    chunk_index: int
    content: str
    score: float
    page_number: Optional[int] = None
    section_title: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True

class RAGRequest(BaseModel):
    query: str
    limit: int = Field(5, ge=1, le=50)
    similarity_threshold: float = Field(0.3, ge=0.0, le=1.0)
    rerank: bool = True

class RAGResponse(BaseModel):
    answer: str
    citations: List[Citation]
    retrieved_chunks: List[RetrievedChunk]

    class Config:
        from_attributes = True
