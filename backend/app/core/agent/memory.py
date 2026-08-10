import abc
import time
import re
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from loguru import logger

from app.core.agent.base import BaseAgent, AgentResult, ExecutionContext
from app.core.agent.state import AgentState, ExecutionStatus
from app.core.agent.prompts import MEMORY_SYSTEM_PROMPT
from app.core.agent.exceptions import (
    MemoryProviderUnavailable, MemoryQueryError, MemoryNotFound, InvalidMemoryRecord,
    MemoryPermissionError, MemoryLimitExceeded, SensitiveMemoryRejected
)
from app.core.ai.base import ChatMessage
from app.services.ai_service import AIService

class MemoryType(str, Enum):
    SESSION = "SESSION"
    CONVERSATION = "CONVERSATION"
    USER_PREFERENCE = "USER_PREFERENCE"
    USER_FACT = "USER_FACT"
    TASK_HISTORY = "TASK_HISTORY"
    DOCUMENT_CONTEXT = "DOCUMENT_CONTEXT"
    LEARNING = "LEARNING"
    PROJECT_CONTEXT = "PROJECT_CONTEXT"
    SYSTEM_KNOWLEDGE = "SYSTEM_KNOWLEDGE"

class MemoryRecord(BaseModel):
    memory_id: str
    user_id: str
    workspace_id: str
    memory_type: MemoryType
    content: str
    source: str
    importance: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    created_at: str
    updated_at: str
    expires_at: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = {}

class MemoryQuery(BaseModel):
    query: str
    user_id: str
    workspace_id: str
    memory_types: Optional[List[MemoryType]] = None
    max_results: int = 5
    min_relevance: float = 0.0
    time_range: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    include_expired: bool = False

class MemoryResult(BaseModel):
    query: str
    memories: List[MemoryRecord]
    context: str
    relevance_score: float
    memory_count: int
    retrieval_time: float
    limitations: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = {}

class MemoryWriteRequest(BaseModel):
    content: str
    memory_type: MemoryType
    importance: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    source: str
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = {}

class BaseMemoryProvider(abc.ABC):
    @abc.abstractmethod
    async def search(self, query: MemoryQuery) -> List[MemoryRecord]:
        pass

    @abc.abstractmethod
    async def store(self, record: MemoryRecord) -> None:
        pass

    @abc.abstractmethod
    async def update(self, record: MemoryRecord) -> None:
        pass

    @abc.abstractmethod
    async def delete(self, memory_id: str, user_id: str, workspace_id: str) -> None:
        pass

    @abc.abstractmethod
    async def get(self, memory_id: str, user_id: str, workspace_id: str) -> Optional[MemoryRecord]:
        pass

    @abc.abstractmethod
    async def health_check(self) -> bool:
        pass

def scrub_sensitive_data(content: str) -> str:
    """
    Scrubs passwords, secrets, or API keys from content.
    """
    patterns = [
        r'(?i)(password|pass|secret|api_key|token|auth_token|private_key)\s*(?:[:=]|is\s+)\s*["\']?[a-zA-Z0-9_\-\.\:\/!@#\$%\^&\*\(\)]+["\']?',
        r'(?i)(sk-)[a-zA-Z0-9]{20,}',
        r'(?i)(AIzaSy)[a-zA-Z0-9_\-]{30,}'
    ]
    cleaned = content
    for pattern in patterns:
        cleaned = re.sub(pattern, r'\1=[REDACTED_SECRET]', cleaned)
    return cleaned

class MockMemoryProvider(BaseMemoryProvider):
    """
    Mock memory provider with user/workspace tenant-isolation filters.
    """
    def __init__(self):
        self.records: Dict[str, MemoryRecord] = {}
        # Prepopulate with isolated memories
        retrieved_time = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.records["mem_1"] = MemoryRecord(
            memory_id="mem_1", user_id="user-A", workspace_id="ws-A",
            memory_type=MemoryType.USER_PREFERENCE, content="User A coding preferences: prefers Java examples.",
            source="chat", importance=0.9, confidence=0.95, created_at=retrieved_time, updated_at=retrieved_time
        )
        self.records["mem_2"] = MemoryRecord(
            memory_id="mem_2", user_id="user-B", workspace_id="ws-B",
            memory_type=MemoryType.USER_PREFERENCE, content="User B coding preferences: prefers Python coding.",
            source="chat", importance=0.8, confidence=0.9, created_at=retrieved_time, updated_at=retrieved_time
        )

    async def search(self, query: MemoryQuery) -> List[MemoryRecord]:
        results = []
        # Word segment matches
        query_words = [w for w in re.findall(r'[a-zA-Z0-9]{3,}', query.query.lower())]
        for rec in self.records.values():
            # Strict tenant-level isolation check
            if rec.user_id != query.user_id or rec.workspace_id != query.workspace_id:
                continue
            if query.memory_types and rec.memory_type not in query.memory_types:
                continue
            # Match if query is wildcard * or shares overlapping keywords
            matched = query.query == "*" or not query_words or any(w in rec.content.lower() for w in query_words)
            if matched:
                results.append(rec)
                
        # Sort by importance descending
        results.sort(key=lambda x: x.importance, reverse=True)
        return results[:query.max_results]

    async def store(self, record: MemoryRecord) -> None:
        self.records[record.memory_id] = record

    async def update(self, record: MemoryRecord) -> None:
        if record.memory_id not in self.records:
            raise MemoryNotFound()
        # Enforce tenant check
        existing = self.records[record.memory_id]
        if existing.user_id != record.user_id or existing.workspace_id != record.workspace_id:
            raise MemoryPermissionError()
        self.records[record.memory_id] = record

    async def delete(self, memory_id: str, user_id: str, workspace_id: str) -> None:
        if memory_id not in self.records:
            raise MemoryNotFound()
        existing = self.records[memory_id]
        if existing.user_id != user_id or existing.workspace_id != workspace_id:
            raise MemoryPermissionError()
        del self.records[memory_id]

    async def get(self, memory_id: str, user_id: str, workspace_id: str) -> Optional[MemoryRecord]:
        rec = self.records.get(memory_id)
        if rec:
            if rec.user_id != user_id or rec.workspace_id != workspace_id:
                raise MemoryPermissionError()
            return rec
        return None

    async def health_check(self) -> bool:
        return True

# Configurable limits
MAX_MEMORY_RESULTS = 10
MAX_MEMORY_CONTEXT_LENGTH = 1024
MAX_MEMORY_CONTENT_LENGTH = 512

class MemoryAgent(BaseAgent):
    """
    MemoryAgent ranks and loads isolated tenant memories.
    """
    def __init__(self, ai_service: AIService, provider: BaseMemoryProvider):
        self.ai_service = ai_service
        self.provider = provider

    @property
    def name(self) -> str:
        return "MemoryAgent"

    @property
    def description(self) -> str:
        return "Determines memory retrieval strategies and ranks relevant items while maintaining tenant isolation."

    def validate_input(self, state: AgentState) -> bool:
        # Require original prompt to match memories
        if not state.get("original_prompt") and "OrchestratorAgent" not in state.get("agent_outputs", {}):
            return False
        return True

    def validate_output(self, result: AgentResult) -> bool:
        if not result.output:
            return False
        return True

    def health_check(self) -> bool:
        return True

    async def execute(self, state: AgentState, context: ExecutionContext) -> AgentResult:
        logger.info("Memory Agent executing retrieval.")
        start_time = time.perf_counter()
        
        prompt = state.get("original_prompt") or ""
        
        # Enforce tenant params
        user_id = context.user_id
        workspace_id = context.workspace_id
        
        if not user_id or not workspace_id:
            raise MemoryPermissionError("Tenant credentials (user_id/workspace_id) missing from ExecutionContext.")

        try:
            # 1. Query mock database provider
            query = MemoryQuery(
                query=prompt or "*",
                user_id=str(user_id),
                workspace_id=str(workspace_id),
                max_results=MAX_MEMORY_RESULTS
            )
            memories = await self.provider.search(query)
            
            # Dev mock/bypass check
            if context.provider == "mock" or "mock" in prompt.lower():
                logger.info("Executing Memory in Mock mode.")
                context_str = "\n".join([f"Relevant: {m.content}" for m in memories])
                mock_res = MemoryResult(
                    query=prompt,
                    memories=memories,
                    context=context_str,
                    relevance_score=0.95,
                    memory_count=len(memories),
                    retrieval_time=time.perf_counter() - start_time
                )
                elapsed = time.perf_counter() - start_time
                return AgentResult(
                    agent_name=self.name,
                    status="success",
                    output=mock_res.model_dump_json(),
                    confidence=0.95,
                    execution_time=elapsed,
                    token_usage={"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25}
                )

            # 2. Extract and format context using AIService
            memories_content = "\n".join([f"Memory {m.memory_id} (Type: {m.memory_type}): {m.content}" for m in memories])
            
            messages = [
                ChatMessage(role="system", content=MEMORY_SYSTEM_PROMPT),
                ChatMessage(role="user", content=f"Retrieved memories:\n{memories_content}\nFormulate context for user request: {prompt}")
            ]
            
            response = await self.ai_service.generate_chat(
                messages=messages,
                provider=context.provider,
                model=context.model,
                user_id=context.user_id
            )

            raw_text = response.content.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text.replace("```json", "", 1)
            if raw_text.endswith("```"):
                raw_text = raw_text.rsplit("```", 1)[0]
            raw_text = raw_text.strip()
            
            res = MemoryResult.model_validate_json(raw_text)
            
            # Scrub any potential leakage in LLM output
            res.context = scrub_sensitive_data(res.context)

            elapsed = time.perf_counter() - start_time
            return AgentResult(
                agent_name=self.name,
                status="success",
                output=res.model_dump_json(),
                confidence=res.relevance_score,
                execution_time=elapsed,
                token_usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            )
        except Exception as e:
            logger.error(f"Memory Agent execution failed: {e}")
            raise e
