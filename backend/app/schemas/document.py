from pydantic import BaseModel, Field
import uuid
import datetime
from typing import Optional, Dict, Any

class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID = Field(..., validation_alias="id")
    filename: str
    mime_type: str
    file_size: int
    status: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True
        populate_by_name = True

class DocumentListItemResponse(BaseModel):
    id: uuid.UUID
    filename: str
    mime_type: str
    file_size: int
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

class DocumentDetailsResponse(BaseModel):
    id: uuid.UUID
    filename: str
    mime_type: str
    file_size: int
    status: str
    page_count: Optional[int] = None
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    extracted_text_length: Optional[int] = None
    processing_error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(None, validation_alias="meta_data")
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True
        populate_by_name = True

class DocumentStatusResponse(BaseModel):
    document_id: uuid.UUID = Field(..., validation_alias="id")
    status: str
    processing_error: Optional[str] = None
    page_count: Optional[int] = None
    extracted_text_length: Optional[int] = None
    updated_at: datetime.datetime
    total_chunks: Optional[int] = None
    processed_chunks: Optional[int] = None
    failed_chunks: Optional[int] = None
    embedding_model: Optional[str] = None
    progress: Optional[float] = None

    class Config:
        from_attributes = True
        populate_by_name = True

class DocumentChunkResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    content_hash: str
    token_count: int
    character_count: int
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    embedding_model: str
    embedding_dimension: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True
        populate_by_name = True
