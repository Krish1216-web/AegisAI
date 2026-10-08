import time
import json
import uuid
from typing import Optional, List, Dict, Any, Union
from loguru import logger
import redis

from app.core.config import settings


class QueueManager:
    """
    Redis-backed reliable queue, distributed lock, and worker coordination manager.
    Supports priority queues, delayed execution (sorted sets), leader election,
    and worker heartbeat tracking.
    """

    DEFAULT_QUEUE = "aegis:queue:default"
    DELAYED_SET = "aegis:queue:delayed"
    LEADER_LOCK_KEY = "aegis:scheduler:leader:lock"
    WORKER_REGISTRY_PREFIX = "aegis:worker:heartbeat:"

    def __init__(self, redis_client: Optional[Union[redis.Redis, Any]] = None):
        if redis_client is not None:
            self.redis = redis_client
        elif getattr(settings, "ENVIRONMENT", "dev") == "test":
            self.redis = None
        else:
            try:
                if getattr(settings, "REDIS_URL", None):
                    self.redis = redis.Redis.from_url(
                        settings.REDIS_URL,
                        decode_responses=True,
                        socket_connect_timeout=1.0,
                        socket_timeout=2.0
                    )
                else:
                    self.redis = redis.Redis(
                        host=settings.REDIS_HOST,
                        port=settings.REDIS_PORT,
                        decode_responses=True,
                        socket_connect_timeout=0.5,
                        socket_timeout=1.0
                    )
            except Exception as e:
                logger.warning(f"Failed to initialize live Redis connection: {e}")
                self.redis = None

    def _get_priority_queue(self, priority: int) -> str:
        if priority >= 80:
            return "aegis:queue:critical"
        elif priority >= 50:
            return "aegis:queue:high"
        elif priority >= 20:
            return "aegis:queue:default"
        return "aegis:queue:low"

    def enqueue(self, job_id: str, priority: int = 50, delay_seconds: float = 0.0) -> bool:
        """
        Enqueues a job into Redis. If delay_seconds > 0, stores in delayed sorted set.
        """
        if self.redis is None:
            return False

        try:
            now = time.time()
            if delay_seconds > 0:
                scheduled_epoch = now + delay_seconds
                self.redis.zadd(self.DELAYED_SET, {str(job_id): scheduled_epoch})
                logger.debug(f"Scheduled delayed job {job_id} at {scheduled_epoch}")
                return True

            queue_name = self._get_priority_queue(priority)
            self.redis.rpush(queue_name, str(job_id))
            logger.debug(f"Pushed job {job_id} to queue '{queue_name}'")
            return True
        except Exception as e:
            logger.error(f"Error enqueueing job {job_id}: {e}")
            return False

    def dequeue(self, timeout_seconds: int = 1) -> Optional[str]:
        """
        Pops a job from priority queues in order: critical -> high -> default -> low.
        """
        if self.redis is None:
            return None

        queues = [
            "aegis:queue:critical",
            "aegis:queue:high",
            "aegis:queue:default",
            "aegis:queue:low"
        ]

        try:
            # BLPOP checks queues in order and pops from the first non-empty list
            result = self.redis.blpop(queues, timeout=timeout_seconds)
            if result:
                # result is tuple: (queue_name, job_id)
                return result[1]
            return None
        except Exception as e:
            logger.error(f"Error dequeuing job: {e}")
            return None

    def poll_delayed_jobs(self, max_batch: int = 100) -> List[str]:
        """
        Moves due jobs from the delayed sorted set into their respective priority queues.
        """
        if self.redis is None:
            return []

        now = time.time()
        due_jobs: List[str] = []

        try:
            # ZRANGEBYSCORE to get jobs ready for execution
            items = self.redis.zrangebyscore(self.DELAYED_SET, 0, now, start=0, num=max_batch)
            if items:
                for item in items:
                    removed = self.redis.zrem(self.DELAYED_SET, item)
                    if removed:
                        due_jobs.append(item)
                        self.enqueue(item, priority=50, delay_seconds=0)
        except Exception as e:
            logger.error(f"Error polling delayed jobs from Redis: {e}")

        return due_jobs

    def acquire_lock(self, key: str, token: str, ttl_seconds: int = 15) -> bool:
        """
        Acquires a distributed lock using SET NX PX.
        """
        if self.redis is None:
            return True  # fallback if redis disabled in local mock

        try:
            return bool(self.redis.set(key, token, nx=True, ex=ttl_seconds))
        except Exception as e:
            logger.error(f"Failed to acquire distributed lock '{key}': {e}")
            return False

    def renew_lock(self, key: str, token: str, ttl_seconds: int = 15) -> bool:
        """
        Extends lock TTL only if caller owns the token.
        """
        if self.redis is None:
            return True

        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        try:
            result = self.redis.eval(lua_script, 1, key, token, ttl_seconds)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to renew lock '{key}': {e}")
            return False

    def release_lock(self, key: str, token: str) -> bool:
        """
        Releases a distributed lock safely using Lua script to verify token ownership.
        """
        if self.redis is None:
            return True

        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        try:
            result = self.redis.eval(lua_script, 1, key, token)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to release distributed lock '{key}': {e}")
            return False

    def register_worker_heartbeat(self, worker_id: str, metadata: Dict[str, Any], ttl_seconds: int = 30) -> None:
        """
        Registers / renews worker heartbeat in Redis.
        """
        if self.redis is None:
            return

        key = f"{self.WORKER_REGISTRY_PREFIX}{worker_id}"
        payload = {
            "worker_id": worker_id,
            "timestamp": time.time(),
            **metadata
        }
        try:
            self.redis.set(key, json.dumps(payload), ex=ttl_seconds)
        except Exception as e:
            logger.warning(f"Failed to register worker heartbeat for {worker_id}: {e}")

    def get_active_workers(self) -> List[Dict[str, Any]]:
        """
        Lists all currently active worker nodes based on heartbeats.
        """
        if self.redis is None:
            return []

        active_workers = []
        try:
            keys = self.redis.keys(f"{self.WORKER_REGISTRY_PREFIX}*")
            for k in keys:
                val = self.redis.get(k)
                if val:
                    try:
                        active_workers.append(json.loads(val))
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Error fetching active workers: {e}")
        return active_workers

    def get_queue_depth(self) -> Dict[str, int]:
        """
        Returns the current number of pending items in each queue.
        """
        depths = {
            "critical": 0,
            "high": 0,
            "default": 0,
            "low": 0,
            "delayed": 0
        }
        if self.redis is None:
            return depths

        try:
            depths["critical"] = self.redis.llen("aegis:queue:critical") or 0
            depths["high"] = self.redis.llen("aegis:queue:high") or 0
            depths["default"] = self.redis.llen("aegis:queue:default") or 0
            depths["low"] = self.redis.llen("aegis:queue:low") or 0
            depths["delayed"] = self.redis.zcard(self.DELAYED_SET) or 0
        except Exception as e:
            logger.error(f"Error getting queue depth: {e}")

        return depths
