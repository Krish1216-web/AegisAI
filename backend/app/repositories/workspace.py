from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.workspace import Organization, Workspace, WorkspaceMember

class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self, db: Session):
        super().__init__(Organization, db)

class WorkspaceRepository(BaseRepository[Workspace]):
    def __init__(self, db: Session):
        super().__init__(Workspace, db)

class WorkspaceMemberRepository(BaseRepository[WorkspaceMember]):
    def __init__(self, db: Session):
        super().__init__(WorkspaceMember, db)
