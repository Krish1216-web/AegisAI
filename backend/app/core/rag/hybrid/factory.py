from typing import Optional
from sqlalchemy.orm import Session
import redis

from app.services.ai_service import AIService
from app.core.rag.retriever import VectorRetriever
from app.core.rag.reranker import SimpleScoreReranker
from app.core.rag.citations import CitationSystem
from app.core.rag.generator import RAGGenerationFlow
from app.core.rag.hybrid.service import HybridRAGService
from app.core.rag.hybrid.models import HybridFusionConfig

class HybridRAGFactory:
    """
    Factory creating fully configured HybridRAGService instances.
    """
    @staticmethod
    def get_hybrid_rag_service(
        db: Session,
        redis_client: Optional[redis.Redis] = None,
        config: Optional[HybridFusionConfig] = None
    ) -> HybridRAGService:
        ai_service = AIService(db, redis_client)
        retriever = VectorRetriever(ai_service)
        reranker = SimpleScoreReranker()
        citation_system = CitationSystem()
        generator = RAGGenerationFlow(ai_service)

        return HybridRAGService(
            db=db,
            redis_client=redis_client,
            retriever=retriever,
            reranker=reranker,
            citation_system=citation_system,
            generator=generator,
            config=config
        )
