import redis
from app.core.config import settings
from typing import Generator
from loguru import logger

# Initialize Redis connection pool
redis_pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    decode_responses=True,
    max_connections=50
)

def get_redis() -> Generator[redis.Redis, None, None]:
    """
    Dependency provider yielding a client instance from the Redis connection pool.
    """
    client = redis.Redis(connection_pool=redis_pool)
    try:
        yield client
    finally:
        client.close()

def check_redis_health() -> bool:
    """
    Pings the Redis host to check if the connection is active.
    """
    try:
        client = redis.Redis(connection_pool=redis_pool)
        return client.ping()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False
