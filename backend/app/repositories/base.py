from sqlalchemy.orm import Session
from typing import Generic, TypeVar, Type, Optional, List
import uuid

ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType]):
    """
    Generic Base Repository pattern implementing CRUD interfaces.
    """
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get_by_id(self, id: uuid.UUID) -> Optional[ModelType]:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj
