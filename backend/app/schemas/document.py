from pydantic import BaseModel
import uuid
from typing import List, Optional

class DocumentBase(BaseModel):
    name: str
    file_path: str

class DocumentCreate(DocumentBase):
    workspace_id: uuid.UUID

class DocumentResponse(DocumentBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    class Config:
        from_attributes = True
