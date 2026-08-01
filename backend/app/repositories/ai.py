from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.ai import Agent, AgentExecution, AgentLog

class AgentRepository(BaseRepository[Agent]):
    def __init__(self, db: Session):
        super().__init__(Agent, db)

class AgentExecutionRepository(BaseRepository[AgentExecution]):
    def __init__(self, db: Session):
        super().__init__(AgentExecution, db)

class AgentLogRepository(BaseRepository[AgentLog]):
    def __init__(self, db: Session):
        super().__init__(AgentLog, db)
