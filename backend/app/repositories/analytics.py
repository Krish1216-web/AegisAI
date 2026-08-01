from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.analytics import AnalyticsEvent, UsageMetrics, APIUsage

class AnalyticsEventRepository(BaseRepository[AnalyticsEvent]):
    def __init__(self, db: Session):
        super().__init__(AnalyticsEvent, db)

class UsageMetricsRepository(BaseRepository[UsageMetrics]):
    def __init__(self, db: Session):
        super().__init__(UsageMetrics, db)

class APIUsageRepository(BaseRepository[APIUsage]):
    def __init__(self, db: Session):
        super().__init__(APIUsage, db)
