import time
import uuid
import json
import hashlib
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import redis
from loguru import logger

from app.core.config import settings
from app.models.rag import RAGQuery
from app.schemas.rag import RAGResponse, Citation, RetrievedChunk
from app.core.rag.base import (
    BaseRetriever,
    BaseReranker,
    BaseContextBuilder,
    BaseCitationSystem,
    BaseGenerationFlow
)

class RAGService:
    def __init__(
        self,
        db: Session,
        redis_client: redis.Redis,
        retriever: BaseRetriever,
        reranker: BaseReranker,
        context_builder: BaseContextBuilder,
        citation_system: BaseCitationSystem,
        generator: BaseGenerationFlow
    ):
        self.db = db
        self.redis = redis_client
        self.retriever = retriever
        self.reranker = reranker
        self.context_builder = context_builder
        self.citation_system = citation_system
        self.generator = generator

    def _get_cache_key(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        query: str,
        limit: int,
        similarity_threshold: float,
        rerank: bool,
        metadata_filters: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        payload = {
            "query": query,
            "limit": limit,
            "similarity_threshold": similarity_threshold,
            "rerank": rerank,
            "metadata_filters": metadata_filters or {},
            "provider": provider or settings.DEFAULT_AI_PROVIDER,
            "model": model or settings.DEFAULT_AI_MODEL
        }
        serialized = json.dumps(payload, sort_keys=True)
        hasher = hashlib.sha256()
        hasher.update(serialized.encode("utf-8"))
        return f"aegis:rag_cache:{workspace_id}:{user_id}:{hasher.hexdigest()}"

    async def query_rag(
        self,
        query: str,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        limit: int = 5,
        similarity_threshold: float = 0.3,
        rerank: bool = True,
        metadata_filters: Optional[Dict[str, Any]] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> RAGResponse:
        active_provider = provider or settings.DEFAULT_AI_PROVIDER
        active_model = model or settings.DEFAULT_AI_MODEL

        # 1. Caching Check
        cache_key = self._get_cache_key(
            workspace_id, user_id, query, limit, similarity_threshold, rerank, metadata_filters, provider, model
        )
        cached_data = self.redis.get(cache_key)
        if cached_data:
            try:
                data = json.loads(cached_data)
                # Log cached query to DB
                db_log = RAGQuery(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    query=query,
                    answer=data["answer"],
                    citations=data["citations"],
                    retrieved_chunks=data["retrieved_chunks"],
                    latency_ms=0,
                    embedding_model=settings.EMBEDDING_MODEL,
                    llm_provider=active_provider,
                    llm_model=active_model,
                    is_cached=True
                )
                self.db.add(db_log)
                self.db.commit()
                
                logger.info(f"RAG query resolved from cache. Key: {cache_key}")
                return RAGResponse.model_validate(data)
            except Exception as e:
                logger.warning(f"Failed to read cached RAG response: {e}")

        # 2. Execution Flow
        start_time = time.time()

        # Step A: Retrieve
        candidates = await self.retriever.retrieve(
            db=self.db,
            query=query,
            user_id=user_id,
            workspace_id=workspace_id,
            limit=limit,
            similarity_threshold=similarity_threshold
        )

        # Step B: Rerank
        if rerank and candidates:
            final_candidates = self.reranker.rerank(
                query=query,
                candidates=candidates,
                metadata_filters=metadata_filters
            )
        else:
            final_candidates = candidates

        # Truncate to final limit
        final_candidates = final_candidates[:limit]

        # Step C: Build Context
        context_str = self.context_builder.build_context(
            candidates=final_candidates,
            max_tokens=getattr(settings, "RAG_CONTEXT_LIMIT_TOKENS", 4000)
        )

        # Step D: Generate Answer
        raw_answer = await self.generator.generate(
            query=query,
            context=context_str,
            provider=active_provider,
            model=active_model,
            temperature=temperature
        )

        # Step E: Citations Validation
        sanitized_answer = self.citation_system.validate_citations(
            answer=raw_answer,
            candidates=final_candidates
        )
        citations_list = self.citation_system.extract_citations(
            answer=sanitized_answer,
            candidates=final_candidates
        )

        # Map candidates to RetrievedChunk schemas
        retrieved_chunks_response = []
        for item in final_candidates:
            chunk = item["chunk"]
            score = item["score"]
            doc_name = "Unknown Source"
            if hasattr(chunk, "document") and chunk.document:
                doc_name = chunk.document.original_filename or chunk.document.filename

            retrieved_chunks_response.append(RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_name=doc_name,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                score=score,
                page_number=chunk.page_number,
                section_title=chunk.section_title
            ))

        latency_ms = int((time.time() - start_time) * 1000)

        # 3. DB Logging
        citations_serialized = [c.model_dump(mode="json") for c in citations_list]
        chunks_serialized = [ch.model_dump(mode="json") for ch in retrieved_chunks_response]

        # Ensure embedding vectors are never saved in the logs
        for ch in chunks_serialized:
            if "embedding" in ch:
                del ch["embedding"]

        db_log = RAGQuery(
            user_id=user_id,
            workspace_id=workspace_id,
            query=query,
            answer=sanitized_answer,
            citations=citations_serialized,
            retrieved_chunks=chunks_serialized,
            latency_ms=latency_ms,
            embedding_model=settings.EMBEDDING_MODEL,
            llm_provider=active_provider,
            llm_model=active_model,
            is_cached=False
        )
        self.db.add(db_log)
        self.db.commit()

        # 4. Save to Redis Cache
        response_obj = RAGResponse(
            answer=sanitized_answer,
            citations=citations_list,
            retrieved_chunks=retrieved_chunks_response
        )
        try:
            self.redis.setex(
                cache_key,
                getattr(settings, "RAG_CACHE_TTL_SECONDS", 3600),
                json.dumps(response_obj.model_dump(mode="json"))
            )
        except Exception as e:
            logger.warning(f"Failed to cache RAG response to Redis: {e}")

        return response_obj
