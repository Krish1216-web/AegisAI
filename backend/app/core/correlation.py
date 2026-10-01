import uuid
import re
import time
from contextvars import ContextVar
from typing import Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context Variables for correlation propagation across threads & async tasks
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id_ctx", default=None)
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id_ctx", default=None)
execution_id_ctx: ContextVar[Optional[str]] = ContextVar("execution_id_ctx", default=None)
job_id_ctx: ContextVar[Optional[str]] = ContextVar("job_id_ctx", default=None)
workflow_id_ctx: ContextVar[Optional[str]] = ContextVar("workflow_id_ctx", default=None)
workspace_id_ctx: ContextVar[Optional[uuid.UUID]] = ContextVar("workspace_id_ctx", default=None)
user_id_ctx: ContextVar[Optional[uuid.UUID]] = ContextVar("user_id_ctx", default=None)

SAFE_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]{1,128}$")


def sanitize_correlation_id(val: Optional[str], default_prefix: str = "req") -> str:
    """
    Validates and sanitizes a client-provided correlation/request identifier,
    preventing header/log injection attacks.
    """
    if not val:
        return f"{default_prefix}_{uuid.uuid4().hex[:16]}"
    cleaned = str(val).strip()
    if SAFE_ID_REGEX.match(cleaned):
        return cleaned
    return f"{default_prefix}_{uuid.uuid4().hex[:16]}"


def get_correlation_context() -> Dict[str, Any]:
    """
    Retrieves the current execution correlation context snapshot.
    """
    ws = workspace_id_ctx.get()
    uid = user_id_ctx.get()
    return {
        "request_id": request_id_ctx.get(),
        "correlation_id": correlation_id_ctx.get(),
        "execution_id": execution_id_ctx.get(),
        "job_id": job_id_ctx.get(),
        "workflow_id": workflow_id_ctx.get(),
        "workspace_id": str(ws) if ws else None,
        "user_id": str(uid) if uid else None,
    }


def set_correlation_context(
    request_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    execution_id: Optional[str] = None,
    job_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    workspace_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None
) -> None:
    """
    Explicitly updates current context variables (useful in worker / scheduler / event threads).
    """
    if request_id is not None:
        request_id_ctx.set(request_id)
    if correlation_id is not None:
        correlation_id_ctx.set(correlation_id)
    if execution_id is not None:
        execution_id_ctx.set(execution_id)
    if job_id is not None:
        job_id_ctx.set(job_id)
    if workflow_id is not None:
        workflow_id_ctx.set(workflow_id)
    if workspace_id is not None:
        workspace_id_ctx.set(workspace_id)
    if user_id is not None:
        user_id_ctx.set(user_id)


def sanitize_header_value(val: Optional[str], max_length: int = 128) -> str:
    """
    Sanitizes any HTTP header value by stripping CRLF, control chars, and bounding length.
    """
    if not val:
        return ""
    # Strip carriage returns, newlines, null bytes and other control chars
    cleaned = re.sub(r"[\r\n\x00-\x1f\x7f-\x9f]", "", str(val))
    return cleaned[:max_length].strip()


def clear_correlation_context() -> None:
    """
    Clears all correlation context variables in the current execution thread/task.
    """
    request_id_ctx.set(None)
    correlation_id_ctx.set(None)
    execution_id_ctx.set(None)
    job_id_ctx.set(None)
    workflow_id_ctx.set(None)
    workspace_id_ctx.set(None)
    user_id_ctx.set(None)


class CorrelationMiddleware(BaseHTTPMiddleware):
    """
    Production middleware that establishes request_id & correlation_id,
    binds to contextvars, records request latency in metrics registry,
    and returns correlation headers in HTTP responses.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        raw_req_id = request.headers.get("X-Request-ID")
        raw_corr_id = request.headers.get("X-Correlation-ID")

        req_id = sanitize_correlation_id(raw_req_id, default_prefix="req")
        corr_id = sanitize_correlation_id(raw_corr_id or req_id, default_prefix="corr")

        request_id_ctx.set(req_id)
        correlation_id_ctx.set(corr_id)

        # Attach to request state
        request.state.request_id = req_id
        request.state.correlation_id = corr_id

        start_time = time.perf_counter()
        status_code = 500
        error_type = None

        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Correlation-ID"] = corr_id
            return response
        except Exception as exc:
            error_type = type(exc).__name__
            raise
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            # Record in unified metrics registry safely
            try:
                from app.core.metrics import metrics_registry
                route_path = request.scope.get("path", "/")
                # Normalize route path to prevent high cardinality
                normalized_route = self._normalize_route(route_path)
                metrics_registry.record_request(
                    method=request.method,
                    route=normalized_route,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    error_type=error_type
                )
            except Exception:
                pass

    def _normalize_route(self, path: str) -> str:
        """
        Normalizes UUIDs and numeric IDs in route paths to preserve bounded metric cardinality.
        Example: /api/v1/workspaces/40b4cd41-fe8a-4ed4... -> /api/v1/workspaces/:id
        """
        # Replace UUIDs
        path_clean = re.sub(r"/[0-9a-fA-F\-]{36}", "/:id", path)
        # Replace numeric IDs
        path_clean = re.sub(r"/\d+", "/:id", path_clean)
        return path_clean
