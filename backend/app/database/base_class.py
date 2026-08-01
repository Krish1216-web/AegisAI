from sqlalchemy.orm import declarative_base, declared_attr
from typing import Any

# Declare declarative base pattern with auto table names configuration
class BaseClass:
    id: Any
    __name__: str

    # Generate __tablename__ automatically using class names
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

Base = declarative_base(cls=BaseClass)
