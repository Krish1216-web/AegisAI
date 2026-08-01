from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.task import Task, TaskExecution

class TaskRepository(BaseRepository[Task]):
    def __init__(self, db: Session):
        super().__init__(Task, db)

class TaskExecutionRepository(BaseRepository[TaskExecution]):
    def __init__(self, db: Session):
        super().__init__(TaskExecution, db)
