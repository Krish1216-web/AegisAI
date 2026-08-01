from app.repositories.base import BaseRepository
from app.models.workspace import Workspace, Organization
from app.models.conversation import Conversation, Message
from app.models.document import Document
from app.models.mcp import MCPServer
from sqlalchemy.orm import Session

class WorkspaceRepository(BaseRepository[Workspace]):
    def __init__(self, db: Session):
        super().__init__(Workspace, db)

class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self, db: Session):
        super().__init__(Organization, db)

class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, db: Session):
        super().__init__(Conversation, db)

class MessageRepository(BaseRepository[Message]):
    def __init__(self, db: Session):
        super().__init__(Message, db)

class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db: Session):
        super().__init__(Document, db)

class MCPServerRepository(BaseRepository[MCPServer]):
    def __init__(self, db: Session):
        super().__init__(MCPServer, db)
