from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.notification import Notification, NotificationPreference

class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, db: Session):
        super().__init__(Notification, db)

class NotificationPreferenceRepository(BaseRepository[NotificationPreference]):
    def __init__(self, db: Session):
        super().__init__(NotificationPreference, db)
