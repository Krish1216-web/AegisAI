import uuid
import json
import math
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from loguru import logger

from app.models.document import DocumentChunk
from app.core.rag.base import BaseRetriever
from app.services.ai_service import AIService

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    dot_product = sum(x * y for x, y in zip(v1, v2))
    norm_v1 = math.sqrt(sum(x * x for x in v1))
    norm_v2 = math.sqrt(sum(x * x for x in v2))
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)

class VectorRetriever(BaseRetriever):
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service

    async def retrieve(
        self,
        db: Session,
        query: str,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        limit: int = 5,
        similarity_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        # Validate input params
        if not user_id or not workspace_id:
            raise ValueError("Missing user_id or workspace_id for tenant filtering.")

        # Generate query embedding
        query_embedding = await self.ai_service.generate_embeddings(query)

        query_filter = [
            DocumentChunk.user_id == user_id,
            DocumentChunk.workspace_id == workspace_id
        ]

        bind = db.get_bind()
        is_postgres = (bind.dialect.name == "postgresql")

        candidates = []

        if HAS_PGVECTOR and is_postgres:
            try:
                # pgvector cosine_distance is 1 - similarity. So similarity is 1 - cosine_distance.
                results = (
                    db.query(DocumentChunk, (1.0 - DocumentChunk.embedding.cosine_distance(query_embedding)).label("similarity"))
                    .filter(*query_filter)
                    .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
                    .limit(limit * 3)
                    .all()
                )
                
                for chunk, sim in results:
                    score = float(sim) if sim is not None else 0.0
                    if score >= similarity_threshold:
                        candidates.append({
                            "chunk": chunk,
                            "score": score
                        })
            except Exception as e:
                logger.error(f"PostgreSQL pgvector search failed, falling back: {e}")
                is_postgres = False # Force fallback

        if not (HAS_PGVECTOR and is_postgres):
            # SQLite fallback
            all_chunks = db.query(DocumentChunk).filter(*query_filter).all()
            for chunk in all_chunks:
                if chunk.embedding:
                    emb = chunk.embedding
                    if isinstance(emb, str):
                        try:
                            emb = json.loads(emb)
                        except Exception:
                            continue
                    
                    score = cosine_similarity(query_embedding, emb)
                    if score >= similarity_threshold:
                        candidates.append({
                            "chunk": chunk,
                            "score": score
                        })
            
            # Sort by score descending
            candidates.sort(key=lambda x: x["score"], reverse=True)
            candidates = candidates[:limit * 3]

        return candidates
