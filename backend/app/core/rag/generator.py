from typing import Optional
from app.core.rag.base import BaseGenerationFlow
from app.core.ai.base import ChatMessage
from app.services.ai_service import AIService

SYSTEM_PROMPT = """You are a precise, secure enterprise AI assistant.
Answer the user's query using ONLY the provided document context. Do not make up facts or extrapolate beyond what is directly stated.

If the provided context does not contain enough information to answer the question, or if it is empty, you must respond with exactly:
"I am sorry, but the provided documents do not contain sufficient information to answer your question."

For every statement you make that is based on a source in the context, cite that source using its source index number inside square brackets, e.g. [1], [2], etc. Place them immediately after the statement they ground.

Context:
{context}"""

SAFE_FALLBACK = "I am sorry, but the provided documents do not contain sufficient information to answer your question."

class RAGGenerationFlow(BaseGenerationFlow):
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service

    async def generate(
        self,
        query: str,
        context: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        if not context.strip():
            return SAFE_FALLBACK

        messages = [
            ChatMessage(role="system", content=SYSTEM_PROMPT.format(context=context)),
            ChatMessage(role="user", content=query)
        ]

        response = await self.ai_service.generate_chat(
            messages=messages,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            bypass_cache=True # cache is managed at the RAG service level
        )

        answer = response.content.strip()
        return answer
