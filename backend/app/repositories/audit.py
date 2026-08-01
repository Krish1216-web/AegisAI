from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.audit import AuditLog, ActivityLog

class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, db: Session):
        super().__init__(AuditLog, db)

class ActivityLogRepository(BaseRepository[ActivityLog]):
    def __init__(self, db: Session):
        super().__init__(ActivityLog, db)
