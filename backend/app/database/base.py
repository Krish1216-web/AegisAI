# Import all SQL models for metadata discovery by Alembic
from app.database.base_class import Base # noqa
from app.models.user import User # noqa
from app.models.role import Role # noqa
