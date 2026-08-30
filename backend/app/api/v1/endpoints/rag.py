import uuid
import json
import time
import hashlib
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import redis
from loguru import logger

from app.database.session import get_db
from app.database.redis import get_redis
from app.api.dependencies import get_current_user, check_rate_limit
from app.models.user import User
from app.schemas.rag import RAGRequest, RAGResponse, Citation, RetrievedChunk, HybridRAGRequest
from app.core.rag.factory import RAGFactory
from app.core.config import settings
from app.models.rag import RAGQuery
from app.core.ai.base import ChatMessage
from app.services.ai_service import AIService
from app.core.rag.generator import SYSTEM_PROMPT, SAFE_FALLBACK
from app.api.v1.endpoints.documents import resolve_workspace_id

router = APIRouter(prefix="/rag", tags=["Cognitive RAG Engine"])

@router.post("/query", response_model=RAGResponse, dependencies=[Depends(check_rate_limit)])
async def query_rag_endpoint(
    payload: RAGRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Retrieves relevant document chunks and generates a grounded response.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    
    rag_service = RAGFactory.get_rag_service(db, redis_client)
    try:
        response = await rag_service.query_rag(
            query=payload.query,
            user_id=current_user.id,
            workspace_id=workspace_id,
            limit=payload.limit,
            similarity_threshold=payload.similarity_threshold,
            rerank=payload.rerank
        )
        return response
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process RAG query: {str(e)}"
        )

@router.post("/hybrid/query", dependencies=[Depends(check_rate_limit)])
async def query_hybrid_rag_endpoint(
    payload: HybridRAGRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Executes Hybrid Vector + Graph RAG retrieval, context fusion, and grounded answer synthesis.
    """
    from app.core.rag.hybrid.factory import HybridRAGFactory
    workspace_id = resolve_workspace_id(current_user, db)
    hybrid_service = HybridRAGFactory.get_hybrid_rag_service(db, redis_client)

    try:
        result = await hybrid_service.query_hybrid(
            query=payload.query,
            user_id=current_user.id,
            workspace_id=workspace_id,
            top_k=payload.top_k,
            graph_depth=payload.graph_depth,
            similarity_threshold=payload.similarity_threshold
        )
        return result
    except Exception as e:
        logger.error(f"Hybrid RAG query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process Hybrid RAG query: {str(e)}"
        )

@router.get("/stream", dependencies=[Depends(check_rate_limit)])
async def stream_rag_endpoint(
    query: str = Query(...),
    limit: int = Query(5, ge=1, le=50),
    similarity_threshold: float = Query(0.3, ge=0.0, le=1.0),
    rerank: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Streams a RAG response back via Server-Sent Events (SSE).
    """
    workspace_id = resolve_workspace_id(current_user, db)
    
    # 1. Check Redis Cache
    rag_service = RAGFactory.get_rag_service(db, redis_client)
    cache_key = rag_service._get_cache_key(
        workspace_id=workspace_id,
        user_id=current_user.id,
        query=query,
        limit=limit,
        similarity_threshold=similarity_threshold,
        rerank=rerank
    )
    
    cached_data = redis_client.get(cache_key)
    if cached_data:
        try:
            data = json.loads(cached_data)
            
            # Log cache hit to DB in background/synchronously
            db_log = RAGQuery(
                user_id=current_user.id,
                workspace_id=workspace_id,
                query=query,
                answer=data["answer"],
                citations=data["citations"],
                retrieved_chunks=data["retrieved_chunks"],
                latency_ms=0,
                embedding_model=settings.EMBEDDING_MODEL,
                llm_provider=settings.DEFAULT_AI_PROVIDER,
                llm_model=settings.DEFAULT_AI_MODEL,
                is_cached=True
            )
            db.add(db_log)
            db.commit()
            
            async def cached_generator():
                yield f"data: {data['answer']}\n\n"
                metadata_payload = {
                    "citations": data["citations"],
                    "retrieved_chunks": data["retrieved_chunks"]
                }
                yield f"data: [METADATA] {json.dumps(metadata_payload)}\n\n"
                yield "data: [DONE]\n\n"
                
            return StreamingResponse(cached_generator(), media_type="text/event-stream")
        except Exception as e:
            logger.warning(f"Error parsing RAG stream cache: {e}")

    # 2. SSE streaming token generator
    async def sse_token_generator():
        start_time = time.time()
        
        # Step A: Retrieve candidates
        try:
            candidates = await rag_service.retriever.retrieve(
                db=db,
                query=query,
                user_id=current_user.id,
                workspace_id=workspace_id,
                limit=limit,
                similarity_threshold=similarity_threshold
            )
        except Exception as e:
            logger.error(f"Retrieve error during stream: {e}")
            yield f"data: [ERROR: Retrieval failed: {str(e)}]\n\n"
            return

        # Step B: Rerank
        if rerank and candidates:
            final_candidates = rag_service.reranker.rerank(
                query=query,
                candidates=candidates
            )
        else:
            final_candidates = candidates

        final_candidates = final_candidates[:limit]

        # Step C: Build context
        context_str = rag_service.context_builder.build_context(
            candidates=final_candidates,
            max_tokens=getattr(settings, "RAG_CONTEXT_LIMIT_TOKENS", 4000)
        )

        full_answer = ""
        
        # Step D: Stream tokens
        if not context_str.strip():
            # Short-circuit to safe fallback
            yield f"data: {SAFE_FALLBACK}\n\n"
            full_answer = SAFE_FALLBACK
        else:
            ai_service = AIService(db, redis_client)
            messages = [
                ChatMessage(role="system", content=SYSTEM_PROMPT.format(context=context_str)),
                ChatMessage(role="user", content=query)
            ]
            try:
                async for token in ai_service.stream_chat(
                    messages=messages,
                    provider=settings.DEFAULT_AI_PROVIDER,
                    model=settings.DEFAULT_AI_MODEL
                ):
                    yield f"data: {token}\n\n"
                    full_answer += token
            except Exception as e:
                logger.error(f"LLM stream error: {e}")
                yield f"data: [ERROR: LLM generation failed: {str(e)}]\n\n"
                return

        # Step E: Citations validation
        sanitized_answer = rag_service.citation_system.validate_citations(
            answer=full_answer,
            candidates=final_candidates
        )
        citations_list = rag_service.citation_system.extract_citations(
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

        # DB Logging
        citations_serialized = [c.model_dump(mode="json") for c in citations_list]
        chunks_serialized = [ch.model_dump(mode="json") for ch in retrieved_chunks_response]

        # Ensure embedding vectors are never saved in the logs
        for ch in chunks_serialized:
            if "embedding" in ch:
                del ch["embedding"]

        try:
            db_log = RAGQuery(
                user_id=current_user.id,
                workspace_id=workspace_id,
                query=query,
                answer=sanitized_answer,
                citations=citations_serialized,
                retrieved_chunks=chunks_serialized,
                latency_ms=latency_ms,
                embedding_model=settings.EMBEDDING_MODEL,
                llm_provider=settings.DEFAULT_AI_PROVIDER,
                llm_model=settings.DEFAULT_AI_MODEL,
                is_cached=False
            )
            db.add(db_log)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log streaming RAG query: {e}")

        # Cache response
        response_obj = RAGResponse(
            answer=sanitized_answer,
            citations=citations_list,
            retrieved_chunks=retrieved_chunks_response
        )
        try:
            redis_client.setex(
                cache_key,
                getattr(settings, "RAG_CACHE_TTL_SECONDS", 3600),
                json.dumps(response_obj.model_dump(mode="json"))
            )
        except Exception as e:
            logger.warning(f"Failed to cache streaming RAG response: {e}")

        # Yield metadata and done signal
        metadata_payload = {
            "citations": citations_serialized,
            "retrieved_chunks": chunks_serialized
        }
        yield f"data: [METADATA] {json.dumps(metadata_payload)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse_token_generator(), media_type="text/event-stream")
