from pydantic import BaseModel
import uuid
from typing import List, Optional

class AuditLogBase(BaseModel):
    action: str
    ip_address: Optional[str] = None
    details: Optional[str] = None

class AuditLogCreate(AuditLogBase):
    user_id: Optional[uuid.UUID] = None

class AuditLogResponse(AuditLogBase):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    class Config:
        from_attributes = True
