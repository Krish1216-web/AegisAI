from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.workflow import Workflow, WorkflowNode, WorkflowExecution, WorkflowLog

class WorkflowRepository(BaseRepository[Workflow]):
    def __init__(self, db: Session):
        super().__init__(Workflow, db)

class WorkflowNodeRepository(BaseRepository[WorkflowNode]):
    def __init__(self, db: Session):
        super().__init__(WorkflowNode, db)

class WorkflowExecutionRepository(BaseRepository[WorkflowExecution]):
    def __init__(self, db: Session):
        super().__init__(WorkflowExecution, db)

class WorkflowLogRepository(BaseRepository[WorkflowLog]):
    def __init__(self, db: Session):
        super().__init__(WorkflowLog, db)
