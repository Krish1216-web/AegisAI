from pydantic import BaseModel
import uuid
from typing import List, Optional

class MCPServerBase(BaseModel):
    name: str
    url: str
    is_active: bool

class MCPServerCreate(MCPServerBase):
    pass

class MCPServerResponse(MCPServerBase):
    id: uuid.UUID
    class Config:
        from_attributes = True
