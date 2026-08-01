from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.memory import Memory, MemoryEmbedding, MemoryCategory

class MemoryCategoryRepository(BaseRepository[MemoryCategory]):
    def __init__(self, db: Session):
        super().__init__(MemoryCategory, db)

class MemoryRepository(BaseRepository[Memory]):
    def __init__(self, db: Session):
        super().__init__(Memory, db)

class MemoryEmbeddingRepository(BaseRepository[MemoryEmbedding]):
    def __init__(self, db: Session):
        super().__init__(MemoryEmbedding, db)
