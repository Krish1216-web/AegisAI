import asyncio
import time
import random
from typing import Dict, Any, Optional, Callable, TypeVar, Coroutine
from loguru import logger

from app.core.mcp.base import (
    BaseMCPClient,
    MCPInitializeResult,
    MCPPingResult,
    MCPClientError,
    MCPConnectionError,
    MCPAuthError,
    MCPValidationError,
    MCPTimeoutError
)
from app.core.mcp.factory import MCPClientFactory
from app.models.mcp import MCPTransport

T = TypeVar("T")

# Non-retryable error classes
NON_RETRYABLE_EXCEPTIONS = (
    MCPAuthError,
    MCPValidationError,
    ValueError,
    TypeError
)

class MCPConnectionManager:
    """
    Manages connection lifecycle, bounded timeouts, transient error retries,
    and health ping measurements for MCP servers.
    """
    DEFAULT_TIMEOUT = 10.0
    MAX_TIMEOUT = 30.0
    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 0.25

    @classmethod
    async def execute_with_retry(
        cls,
        operation: Callable[[], Coroutine[Any, Any, T]],
        max_retries: int = MAX_RETRIES,
        base_delay: float = BASE_RETRY_DELAY
    ) -> T:
        """
        Executes an asynchronous operation with exponential backoff and jitter
        for transient network/server failures. Immediately raises auth & validation errors.
        """
        attempt = 0
        last_exception = None

        while attempt < max_retries:
            attempt += 1
            try:
                return await operation()
            except NON_RETRYABLE_EXCEPTIONS as e:
                logger.warning(f"Non-retryable MCP error encountered on attempt {attempt}: {e}")
                raise e
            except Exception as e:
                last_exception = e
                if attempt >= max_retries:
                    logger.error(f"MCP operation failed after {attempt} attempts: {e}")
                    break
                
                # Exponential backoff with jitter
                delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0.01, 0.1)
                logger.warning(f"Transient MCP failure (attempt {attempt}/{max_retries}): {e}. Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)

        if isinstance(last_exception, MCPClientError):
            raise last_exception
        raise MCPConnectionError(f"Connection failed after {max_retries} attempts: {last_exception}")

    @classmethod
    async def connect_and_initialize(
        cls,
        server_url: str,
        transport: MCPTransport = MCPTransport.SSE,
        auth_config: Optional[Dict[str, Any]] = None,
        timeout: float = DEFAULT_TIMEOUT
    ) -> tuple[BaseMCPClient, MCPInitializeResult]:
        """
        Instantiates MCP client, enforces bounded timeout, and completes protocol handshake.
        """
        effective_timeout = min(max(timeout, 1.0), cls.MAX_TIMEOUT)
        client = MCPClientFactory.create_client(
            server_url=server_url,
            transport=transport,
            auth_config=auth_config,
            timeout=effective_timeout
        )

        async def _init_call():
            try:
                return await asyncio.wait_for(client.initialize(), timeout=effective_timeout)
            except asyncio.TimeoutError:
                raise MCPTimeoutError(f"Connection/Handshake timed out after {effective_timeout}s with server: {server_url}")

        try:
            init_res = await cls.execute_with_retry(_init_call, max_retries=cls.MAX_RETRIES)
            return client, init_res
        except Exception as e:
            await client.close()
            raise e

    @classmethod
    async def ping_health(
        cls,
        server_url: str,
        transport: MCPTransport = MCPTransport.SSE,
        auth_config: Optional[Dict[str, Any]] = None,
        timeout: float = 5.0
    ) -> MCPPingResult:
        """
        Executes a rapid ping/liveness probe against the server.
        """
        effective_timeout = min(timeout, 10.0)
        client = MCPClientFactory.create_client(
            server_url=server_url,
            transport=transport,
            auth_config=auth_config,
            timeout=effective_timeout
        )

        try:
            res = await asyncio.wait_for(client.ping(), timeout=effective_timeout)
            return res
        except asyncio.TimeoutError:
            raise MCPTimeoutError(f"Ping probe timed out after {effective_timeout}s for {server_url}")
        finally:
            await client.close()
