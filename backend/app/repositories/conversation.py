from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository
from app.models.conversation import Conversation, Message, ConversationParticipant

class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, db: Session):
        super().__init__(Conversation, db)

class MessageRepository(BaseRepository[Message]):
    def __init__(self, db: Session):
        super().__init__(Message, db)

class ConversationParticipantRepository(BaseRepository[ConversationParticipant]):
    def __init__(self, db: Session):
        super().__init__(ConversationParticipant, db)
