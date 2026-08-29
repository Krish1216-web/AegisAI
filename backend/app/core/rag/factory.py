import redis
from sqlalchemy.orm import Session

from app.services.ai_service import AIService
from app.core.rag.retriever import VectorRetriever
from app.core.rag.reranker import SimpleScoreReranker
from app.core.rag.context import ContextBuilder
from app.core.rag.citations import CitationSystem
from app.core.rag.generator import RAGGenerationFlow
from app.core.rag.service import RAGService

class RAGFactory:
    @staticmethod
    def get_rag_service(db: Session, redis_client: redis.Redis) -> RAGService:
        ai_service = AIService(db, redis_client)
        retriever = VectorRetriever(ai_service)
        reranker = SimpleScoreReranker()
        context_builder = ContextBuilder()
        citation_system = CitationSystem()
        generator = RAGGenerationFlow(ai_service)
        
        return RAGService(
            db=db,
            redis_client=redis_client,
            retriever=retriever,
            reranker=reranker,
            context_builder=context_builder,
            citation_system=citation_system,
            generator=generator
        )
