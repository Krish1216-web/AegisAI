from pydantic import BaseModel
import uuid
from typing import List, Optional

class AnalyticsEventBase(BaseModel):
    event_type: str
    payload: Optional[str] = None

class AnalyticsEventCreate(AnalyticsEventBase):
    pass

class AnalyticsEventResponse(AnalyticsEventBase):
    id: uuid.UUID
    class Config:
        from_attributes = True
