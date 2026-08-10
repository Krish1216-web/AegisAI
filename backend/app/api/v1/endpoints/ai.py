from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import time
import uuid

from app.database.session import get_db
from app.database.redis import get_redis
from app.api.dependencies import get_current_user
from app.models.user import User
from app.core.ai.base import ChatMessage, ChatResponse
from app.services.ai_service import AIService
from app.core.config import settings
import redis

router = APIRouter(prefix="/ai", tags=["AI Provider Engine"])

# We will declare Pydantic input models for endpoints
from pydantic import BaseModel

class ChatRequestSchema(BaseModel):
    messages: List[ChatMessage]
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    bypass_cache: Optional[bool] = False

@router.post("/chat", response_model=ChatResponse)
async def generate_chat_response(
    payload: ChatRequestSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Sends a prompt history list to the resolved provider and returns a unified response.
    """
    ai_service = AIService(db, redis_client)
    return await ai_service.generate_chat(
        messages=payload.messages,
        provider=payload.provider,
        model=payload.model,
        user_id=current_user.id,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        bypass_cache=payload.bypass_cache
    )

@router.post("/stream")
async def stream_chat_response(
    payload: ChatRequestSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Streams output tokens back to the client.
    """
    ai_service = AIService(db, redis_client)
    
    async def token_generator():
        try:
            async for chunk in ai_service.stream_chat(
                messages=payload.messages,
                provider=payload.provider,
                model=payload.model,
                temperature=payload.temperature,
                max_tokens=payload.max_tokens
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR: {str(e)}]\n\n"
            
    return StreamingResponse(token_generator(), media_type="text/event-stream")

@router.get("/providers", response_model=List[str])
def get_available_providers(current_user: User = Depends(get_current_user)):
    """
    Returns active LLM service integrations.
    """
    return ["openai", "gemini", "anthropic", "mock"]

@router.get("/health")
def check_providers_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Scans provider health metrics.
    """
    # Returns simulated/mock statuses of configured keys
    return {
        "status": "ONLINE",
        "timestamp": time.time(),
        "providers": {
            "openai": "AVAILABLE" if settings.OPENAI_API_KEY else "MOCK_MODE",
            "gemini": "AVAILABLE" if settings.GEMINI_API_KEY else "MOCK_MODE",
            "anthropic": "AVAILABLE" if settings.ANTHROPIC_API_KEY else "MOCK_MODE"
        }
    }
