from pydantic import BaseModel
import uuid
from typing import List, Optional

class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: str

class AgentCreate(AgentBase):
    pass

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None

class AgentResponse(AgentBase):
    id: uuid.UUID
    class Config:
        from_attributes = True

class AgentExecutionBase(BaseModel):
    status: str
    input_data: Optional[str] = None
    output_data: Optional[str] = None

class AgentExecutionCreate(AgentExecutionBase):
    agent_id: uuid.UUID

class AgentExecutionResponse(AgentExecutionBase):
    id: uuid.UUID
    agent_id: uuid.UUID
    class Config:
        from_attributes = True
