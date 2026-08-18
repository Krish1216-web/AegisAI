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

    class Config:
        from_attributes = True
        populate_by_name = True
