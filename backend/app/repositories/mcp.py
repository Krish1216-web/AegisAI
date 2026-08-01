from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.mcp import MCPServer, MCPTool, MCPConnection

class MCPServerRepository(BaseRepository[MCPServer]):
    def __init__(self, db: Session):
        super().__init__(MCPServer, db)

class MCPToolRepository(BaseRepository[MCPTool]):
    def __init__(self, db: Session):
        super().__init__(MCPTool, db)

class MCPConnectionRepository(BaseRepository[MCPConnection]):
    def __init__(self, db: Session):
        super().__init__(MCPConnection, db)
