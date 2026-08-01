from pydantic import BaseModel
import uuid
from typing import List, Optional

class MemoryCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class MemoryCategoryCreate(MemoryCategoryBase):
    pass

class MemoryCategoryResponse(MemoryCategoryBase):
    id: uuid.UUID
    class Config:
        from_attributes = True

class MemoryBase(BaseModel):
    content: str

class MemoryCreate(MemoryBase):
    workspace_id: uuid.UUID
    category_id: uuid.UUID

class MemoryResponse(MemoryBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    category_id: uuid.UUID
    class Config:
        from_attributes = True
