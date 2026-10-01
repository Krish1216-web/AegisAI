import time
import math
import threading
from collections import defaultdict, deque
from typing import Dict, Any, List, Optional
from loguru import logger

from app.core.mcp.security import CredentialStore


class MetricsRegistry:
    """
    Unified In-Memory Production Metrics Registry.
    Aggregates request latencies (p50, p90, p95, p99), error categories,
    database connection stats, queue depths, worker execution metrics,
    and platform subsystem telemetry with strict bounded-cardinality controls.
    """

    MAX_LATENCY_SAMPLES = 5000
    MAX_ROUTES_TRACKED = 200

    def __init__(self):
        self._lock = threading.Lock()
        self._start_time = time.time()

        # 1. Request & HTTP Metrics
        self._total_requests = 0
        self._status_counts: Dict[str, int] = defaultdict(int) # "2xx", "3xx", "4xx", "5xx"
        self._error_category_counts: Dict[str, int] = defaultdict(int)
        self._latencies: deque = deque(maxlen=self.MAX_LATENCY_SAMPLES)
        self._route_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "errors": 0, "latencies": deque(maxlen=500)}
        )

        # 2. Database Metrics
        self._db_checkouts = 0
        self._db_rollbacks = 0
        self._db_connection_failures = 0
        self._db_pool_exhaustions = 0
        self._db_query_latencies: deque = deque(maxlen=1000)

        # 3. Redis & Queue Metrics
        self._redis_operations = 0
        self._redis_errors = 0
        self._job_claim_failures = 0
        self._lock_contentions = 0

        # 4. Worker & Scheduler Metrics
        self._jobs_queued = 0
        self._jobs_started = 0
        self._jobs_succeeded = 0
        self._jobs_failed = 0
        self._jobs_retried = 0
        self._jobs_dead_lettered = 0
        self._jobs_cancelled = 0
        self._jobs_stale_recovered = 0
        self._scheduler_cycles = 0
        self._scheduler_schedules_triggered = 0
        self._scheduler_duplicate_suppressions = 0

        # 5. Domain Capability Metrics
        self._agent_invocations = 0
        self._agent_tool_calls = 0
        self._agent_critic_rejections = 0
        self._rag_queries = 0
        self._rag_retrievals = 0
        self._graph_traversals = 0
        self._mcp_tool_invocations = 0
        self._mcp_security_blocks = 0
        self._workflow_runs = 0

    @staticmethod
    def _calculate_percentile(samples: List[float], percentile: float) -> float:
        """Computes deterministic percentile with linear interpolation."""
        if not samples:
            return 0.0
        sorted_s = sorted(samples)
        k = (len(sorted_s) - 1) * (percentile / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return round(float(sorted_s[int(k)]), 2)
        d0 = sorted_s[int(f)] * (c - k)
        d1 = sorted_s[int(c)] * (k - f)
        return round(float(d0 + d1), 2)

    def record_request(
        self,
        method: str,
        route: str,
        status_code: int,
        duration_ms: float,
        error_type: Optional[str] = None
    ) -> None:
        """Records incoming HTTP request outcome, latency, and status class."""
        status_class = f"{status_code // 100}xx"
        with self._lock:
            self._total_requests += 1
            self._status_counts[status_class] += 1
            self._latencies.append(duration_ms)

            if len(self._route_stats) < self.MAX_ROUTES_TRACKED or route in self._route_stats:
                stat = self._route_stats[f"{method.upper()} {route}"]
                stat["count"] += 1
                if status_code >= 400:
                    stat["errors"] += 1
                stat["latencies"].append(duration_ms)

            if status_code >= 400 and error_type:
                self._error_category_counts[error_type] += 1

    def record_error_category(self, category: str) -> None:
        """Records a domain or infrastructure error category."""
        with self._lock:
            self._error_category_counts[category] += 1

    def record_db_query(self, duration_ms: float, is_rollback: bool = False, is_failure: bool = False) -> None:
        """Records database query latency and transactional state."""
        with self._lock:
            self._db_checkouts += 1
            self._db_query_latencies.append(duration_ms)
            if is_rollback:
                self._db_rollbacks += 1
            if is_failure:
                self._db_connection_failures += 1

    def record_db_pool_exhaustion(self) -> None:
        with self._lock:
            self._db_pool_exhaustions += 1

    def record_redis_op(self, is_error: bool = False, is_lock_contention: bool = False) -> None:
        with self._lock:
            self._redis_operations += 1
            if is_error:
                self._redis_errors += 1
            if is_lock_contention:
                self._lock_contentions += 1

    def record_job_lifecycle(self, event_type: str) -> None:
        """Tracks background worker job transitions."""
        with self._lock:
            if event_type == "queued":
                self._jobs_queued += 1
            elif event_type == "started":
                self._jobs_started += 1
            elif event_type == "succeeded":
                self._jobs_succeeded += 1
            elif event_type == "failed":
                self._jobs_failed += 1
            elif event_type == "retried":
                self._jobs_retried += 1
            elif event_type == "dead_lettered":
                self._jobs_dead_lettered += 1
            elif event_type == "cancelled":
                self._jobs_cancelled += 1
            elif event_type == "stale_recovered":
                self._jobs_stale_recovered += 1

    def record_scheduler_event(self, event_type: str, count: int = 1) -> None:
        with self._lock:
            if event_type == "cycle":
                self._scheduler_cycles += count
            elif event_type == "schedule_triggered":
                self._scheduler_schedules_triggered += count
            elif event_type == "duplicate_suppressed":
                self._scheduler_duplicate_suppressions += count

    def record_capability_telemetry(self, domain: str, action: str, count: int = 1) -> None:
        with self._lock:
            if domain == "agent":
                if action == "invocation":
                    self._agent_invocations += count
                elif action == "tool_call":
                    self._agent_tool_calls += count
                elif action == "critic_rejection":
                    self._agent_critic_rejections += count
            elif domain == "rag":
                if action == "query":
                    self._rag_queries += count
                elif action == "retrieval":
                    self._rag_retrievals += count
            elif domain == "graph":
                self._graph_traversals += count
            elif domain == "mcp":
                if action == "tool":
                    self._mcp_tool_invocations += count
                elif action == "security_block":
                    self._mcp_security_blocks += count
            elif domain == "workflow":
                self._workflow_runs += count

    def get_request_metrics(self) -> Dict[str, Any]:
        """Returns request counts, status distributions, and latency percentiles."""
        with self._lock:
            samples = list(self._latencies)
            total = self._total_requests
            status_dist = dict(self._status_counts)
            errors = dict(self._error_category_counts)
            uptime = round(time.time() - self._start_time, 2)

            routes_out = {}
            for r_key, stat in list(self._route_stats.items()):
                r_samples = list(stat["latencies"])
                routes_out[r_key] = {
                    "count": stat["count"],
                    "errors": stat["errors"],
                    "p50_ms": self._calculate_percentile(r_samples, 50),
                    "p95_ms": self._calculate_percentile(r_samples, 95),
                    "p99_ms": self._calculate_percentile(r_samples, 99)
                }

        p50 = self._calculate_percentile(samples, 50)
        p90 = self._calculate_percentile(samples, 90)
        p95 = self._calculate_percentile(samples, 95)
        p99 = self._calculate_percentile(samples, 99)
        avg = round(sum(samples) / len(samples), 2) if samples else 0.0
        min_v = round(min(samples), 2) if samples else 0.0
        max_v = round(max(samples), 2) if samples else 0.0

        throughput_rps = round(total / max(1.0, uptime), 2)
        err_5xx = status_dist.get("5xx", 0)
        error_rate_pct = round((err_5xx / max(1, total)) * 100.0, 2)

        return {
            "uptime_seconds": uptime,
            "total_requests": total,
            "throughput_rps": throughput_rps,
            "error_rate_percentage": error_rate_pct,
            "status_code_distribution": status_dist,
            "error_categories": errors,
            "latency_ms": {
                "min": min_v,
                "mean": avg,
                "p50": p50,
                "p90": p90,
                "p95": p95,
                "p99": p99,
                "max": max_v
            },
            "routes": routes_out
        }

    def get_infrastructure_metrics(self) -> Dict[str, Any]:
        """Returns database, Redis, worker, and scheduler metrics."""
        with self._lock:
            db_latencies = list(self._db_query_latencies)
            return {
                "database": {
                    "checkouts_total": self._db_checkouts,
                    "rollbacks_total": self._db_rollbacks,
                    "connection_failures": self._db_connection_failures,
                    "pool_exhaustions": self._db_pool_exhaustions,
                    "query_latency_ms": {
                        "p50": self._calculate_percentile(db_latencies, 50),
                        "p95": self._calculate_percentile(db_latencies, 95)
                    }
                },
                "redis": {
                    "operations_total": self._redis_operations,
                    "operation_errors": self._redis_errors,
                    "lock_contentions": self._lock_contentions
                },
                "worker": {
                    "jobs_queued": self._jobs_queued,
                    "jobs_started": self._jobs_started,
                    "jobs_succeeded": self._jobs_succeeded,
                    "jobs_failed": self._jobs_failed,
                    "jobs_retried": self._jobs_retried,
                    "jobs_dead_lettered": self._jobs_dead_lettered,
                    "jobs_cancelled": self._jobs_cancelled,
                    "jobs_stale_recovered": self._jobs_stale_recovered
                },
                "scheduler": {
                    "cycles_total": self._scheduler_cycles,
                    "schedules_triggered": self._scheduler_schedules_triggered,
                    "duplicate_suppressions": self._scheduler_duplicate_suppressions
                }
            }

    def get_domain_telemetry(self) -> Dict[str, Any]:
        """Returns platform capability metrics across agents, RAG, Graph, MCP, and workflows."""
        with self._lock:
            return {
                "agent": {
                    "invocations": self._agent_invocations,
                    "tool_calls": self._agent_tool_calls,
                    "critic_rejections": self._agent_critic_rejections
                },
                "rag": {
                    "queries": self._rag_queries,
                    "retrievals": self._rag_retrievals
                },
                "graph": {
                    "traversals": self._graph_traversals
                },
                "mcp": {
                    "tool_invocations": self._mcp_tool_invocations,
                    "security_blocks": self._mcp_security_blocks
                },
                "workflow": {
                    "runs_total": self._workflow_runs
                }
            }

    def reset(self) -> None:
        """Resets all metrics counters (primarily for testing)."""
        with self._lock:
            self._total_requests = 0
            self._status_counts.clear()
            self._error_category_counts.clear()
            self._latencies.clear()
            self._route_stats.clear()
            self._db_checkouts = 0
            self._db_rollbacks = 0
            self._db_connection_failures = 0
            self._db_pool_exhaustions = 0
            self._db_query_latencies.clear()
            self._redis_operations = 0
            self._redis_errors = 0
            self._lock_contentions = 0
            self._jobs_queued = 0
            self._jobs_started = 0
            self._jobs_succeeded = 0
            self._jobs_failed = 0
            self._jobs_retried = 0
            self._jobs_dead_lettered = 0
            self._jobs_cancelled = 0
            self._jobs_stale_recovered = 0
            self._scheduler_cycles = 0
            self._scheduler_schedules_triggered = 0
            self._scheduler_duplicate_suppressions = 0
            self._agent_invocations = 0
            self._agent_tool_calls = 0
            self._agent_critic_rejections = 0
            self._rag_queries = 0
            self._rag_retrievals = 0
            self._graph_traversals = 0
            self._mcp_tool_invocations = 0
            self._mcp_security_blocks = 0
            self._workflow_runs = 0
            self._start_time = time.time()


# Global Singleton Metrics Registry
metrics_registry = MetricsRegistry()
