from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.document import Document, DocumentChunk, DocumentEmbedding

class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db: Session):
        super().__init__(Document, db)

class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    def __init__(self, db: Session):
        super().__init__(DocumentChunk, db)

class DocumentEmbeddingRepository(BaseRepository[DocumentEmbedding]):
    def __init__(self, db: Session):
        super().__init__(DocumentEmbedding, db)
