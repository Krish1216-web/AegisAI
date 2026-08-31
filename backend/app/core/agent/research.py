import abc
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from loguru import logger

from app.core.agent.base import BaseAgent, AgentResult, ExecutionContext
from app.core.agent.state import AgentState, ExecutionStatus
from app.core.agent.prompts import RESEARCH_SYSTEM_PROMPT
from app.core.agent.exceptions import InvalidResearchRequest, ResearchTimeout, NoResultsFound, InvalidResearchResult
from app.core.ai.base import ChatMessage
from app.services.ai_service import AIService

class ResearchRequest(BaseModel):
    query: str
    research_goal: str
    required_information: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    max_sources: int = 5
    language: str = "en"
    time_range: Optional[str] = None
    source_preferences: List[str] = Field(default_factory=list)
    workspace_id: str
    user_id: str
    execution_id: str

class ResearchSource(BaseModel):
    source_id: str
    title: str
    url: Optional[str] = None
    source_type: str # web | knowledge_base | document
    publisher: Optional[str] = None
    published_at: Optional[str] = None
    retrieved_at: str
    relevance_score: float
    content_reference: str
    metadata: Dict[str, Any] = {}

class ResearchFinding(BaseModel):
    finding_id: str
    title: str
    claim: str
    supporting_evidence: str
    source_ids: List[str]
    confidence: float
    relevance: float
    timestamp: str

class ResearchResult(BaseModel):
    query: str
    summary: str
    findings: List[ResearchFinding]
    sources: List[ResearchSource]
    confidence: float
    research_time: float
    source_count: int
    limitations: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = {}

class BaseResearchProvider(abc.ABC):
    @abc.abstractmethod
    async def search(self, query: str, max_results: int = 5) -> List[ResearchSource]:
        pass

    @abc.abstractmethod
    async def retrieve(self, source_id: str) -> str:
        pass

    @abc.abstractmethod
    async def health_check(self) -> bool:
        pass

class MockResearchProvider(BaseResearchProvider):
    """
    Mock search provider for air-gapped unit testing and local development runs.
    """
    async def search(self, query: str, max_results: int = 5) -> List[ResearchSource]:
        # Return deterministic mock research sources
        logger.info(f"Mock Research search query received: {query}")
        if not query:
            return []
            
        retrieved_time = time.strftime("%Y-%m-%d")
        return [
            ResearchSource(
                source_id="mock_src_1",
                title="Mock Research Paper: Blockchain Applications in Enterprise OS",
                url="http://mock-science.enterprise/blockchain-os.pdf",
                source_type="document",
                publisher="Mock Science Press",
                published_at="2026-01-15",
                retrieved_at=retrieved_time,
                relevance_score=0.95,
                content_reference="Mock citation: Enterprise multi-agent operating systems benefit from blockchain consensus algorithms to distribute task queues safely."
            )
        ]

    async def retrieve(self, source_id: str) -> str:
        if source_id == "mock_src_1":
            return "Consensus-based task queuing models prevent agent execution deadlocks."
        raise NoResultsFound(f"Mock source {source_id} not found.")

    async def health_check(self) -> bool:
        return True

import asyncio
import httpx
from urllib.parse import urlparse
from app.core.config import settings

class TavilyResearchProvider(BaseResearchProvider):
    """
    Tavily Search implementation of the Research provider interface.
    """
    def __init__(self, api_key: str, timeout: float = 15.0):
        self.api_key = api_key
        self.timeout = timeout
        self.url = "https://api.tavily.com/search"

    async def search(self, query: str, max_results: int = 5) -> List[ResearchSource]:
        headers = {"Content-Type": "application/json"}
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "advanced",
            "include_answer": False,
            "include_raw_content": False
        }
        
        retries = 3
        backoff = 1.0
        
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(self.url, json=payload, headers=headers)
                    
                    if response.status_code == 401:
                        logger.error("Tavily Search authentication failure: Invalid API Key.")
                        return []
                    elif response.status_code == 429:
                        logger.warning(f"Tavily Search rate limited (attempt {attempt + 1}/{retries}).")
                        if attempt == retries - 1:
                            return []
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                    elif response.status_code >= 500:
                        logger.warning(f"Tavily Search transient server failure {response.status_code} (attempt {attempt + 1}/{retries}).")
                        if attempt == retries - 1:
                            return []
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                    elif response.status_code != 200:
                        logger.error(f"Tavily Search failed with status {response.status_code}: {response.text}")
                        return []
                        
                    data = response.json()
                    results = data.get("results", [])
                    if not results:
                        return []
                        
                    sources = []
                    retrieved_time = time.strftime("%Y-%m-%dT%H:%M:%SZ")
                    for i, r in enumerate(results):
                        url = r.get("url") or ""
                        domain = "web"
                        if url:
                            try:
                                parsed = urlparse(url)
                                domain = parsed.netloc or "web"
                            except Exception:
                                pass
                                
                        score = r.get("score", 0.7)
                        sources.append(ResearchSource(
                            source_id=f"src_{i+1}",
                            title=r.get("title") or "Search Result",
                            url=url or None,
                            source_type="web",
                            publisher=domain,
                            published_at=None,
                            retrieved_at=retrieved_time,
                            relevance_score=float(score),
                            content_reference=r.get("content") or "",
                            metadata={}
                        ))
                    return sources
            except httpx.TimeoutException:
                logger.warning(f"Tavily Search request timed out (attempt {attempt + 1}/{retries}).")
                if attempt == retries - 1:
                    raise ResearchTimeout("Tavily research provider search request timed out.")
                await asyncio.sleep(backoff)
                backoff *= 2
            except Exception as e:
                logger.error(f"Tavily Search encountered unexpected error: {e}")
                if attempt == retries - 1:
                    return []
                await asyncio.sleep(backoff)
                backoff *= 2
        return []

    async def retrieve(self, source_id: str) -> str:
        return ""

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        return True

class ResearchProviderFactory:
    @staticmethod
    def get_provider() -> BaseResearchProvider:
        provider_name = settings.RESEARCH_PROVIDER.lower()
        if provider_name == "tavily":
            key = getattr(settings, "TAVILY_API_KEY", None)
            if not key or key == "":
                if settings.ENVIRONMENT != "prod":
                    return MockResearchProvider()
                raise ValueError("Tavily API Key is missing in production environment.")
            return TavilyResearchProvider(api_key=key)
        elif provider_name == "mock":
            return MockResearchProvider()
        else:
            if settings.ENVIRONMENT != "prod":
                return MockResearchProvider()
            raise ValueError(f"Unsupported research provider: {provider_name}")

# Configurable limits
MAX_SOURCES = 10
MAX_QUERY_LENGTH = 100
MAX_RETRIEVAL_SIZE = 1024 * 1024 # 1MB

class ResearchAgent(BaseAgent):
    """
    ResearchAgent parses plan tasks and runs search providers.
    """
    def __init__(self, ai_service: AIService, provider: BaseResearchProvider):
        self.ai_service = ai_service
        self.provider = provider

    @property
    def name(self) -> str:
        return "ResearchAgent"

    @property
    def description(self) -> str:
        return "Gathers raw information, extracts verifiable claims, and links claims to sources."

    def validate_input(self, state: AgentState) -> bool:
        # Require a detailed plan or original prompt
        if not state.get("original_prompt") and "PlannerAgent" not in state.get("agent_outputs", {}):
            return False
        return True

    def validate_output(self, result: AgentResult) -> bool:
        if not result.output:
            return False
        return True

    def health_check(self) -> bool:
        return True

    async def execute(self, state: AgentState, context: ExecutionContext) -> AgentResult:
        logger.info("Research Agent initiating analysis.")
        start_time = time.perf_counter()
        
        prompt = state.get("original_prompt") or ""
        if len(prompt) > MAX_QUERY_LENGTH:
            prompt = prompt[:MAX_QUERY_LENGTH] # Enforce strict query constraints

        try:
            # 1. Query the research provider
            sources = await self.provider.search(prompt, max_results=MAX_SOURCES)
            if not sources:
                raise NoResultsFound("No research sources found matching prompt.")
                
            # If mock mode execution is requested via MockProvider, return local response
            if context.provider == "mock" or "mock" in prompt.lower():
                logger.info("Executing Research in Mock mode.")
                mock_res = ResearchResult(
                    query=prompt,
                    summary="Mock research consolidation summary.",
                    findings=[
                        ResearchFinding(
                            finding_id="finding_1",
                            title="Mock blockchain consensus",
                            claim="Blockchain coordinates multi-agent consensus",
                            supporting_evidence="Distributed task queues prevent deadlocks",
                            source_ids=["mock_src_1"],
                            confidence=0.95,
                            relevance=0.9,
                            timestamp="2026-08-10"
                        )
                    ],
                    sources=sources,
                    confidence=0.95,
                    research_time=time.perf_counter() - start_time,
                    source_count=1,
                    limitations=["Running with mock research data"]
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

            # 2. Consolidate and extract using AIService
            sources_content = "\n".join([f"Source {s.source_id}: {s.content_reference}" for s in sources])
            
            messages = [
                ChatMessage(role="system", content=RESEARCH_SYSTEM_PROMPT),
                ChatMessage(role="user", content=f"Retrieved content:\n{sources_content}\nAnalyze query: {prompt}")
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
            
            # Validation checks
            res = ResearchResult.model_validate_json(raw_text)
            
            # Check source ID references exist
            available_src_ids = [s.source_id for s in sources]
            for f in res.findings:
                for src_id in f.source_ids:
                    if src_id not in available_src_ids:
                        raise InvalidResearchResult(f"Finding references non-existent source: {src_id}")

            elapsed = time.perf_counter() - start_time
            return AgentResult(
                agent_name=self.name,
                status="success",
                output=res.model_dump_json(),
                confidence=res.confidence,
                execution_time=elapsed,
                token_usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            )
        except Exception as e:
            logger.error(f"Research Agent failed: {e}")
            raise e
