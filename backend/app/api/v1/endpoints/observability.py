import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.core.metrics import metrics_registry
from app.services.operational_alerts import operational_alert_engine
from app.schemas.observability import (
    ObservabilityOverviewResponse,
    RequestMetricsResponse,
    InfrastructureMetricsResponse,
    DomainMetricsResponse,
    OperationalAlertResponse,
    OperationalAlertListResponse,
    IncidentTimelineResponse
)

router = APIRouter(prefix="/observability", tags=["Production Observability"])


def _validate_observability_access(user: User) -> None:
    """Validates that the user has tenant access or administrative permissions."""
    role_name = user.role.name if (user.role and hasattr(user.role, "name")) else (str(user.role) if user.role else "viewer")
    
    if role_name.lower() in ["admin", "super admin", "owner"] or getattr(user, "workspace_id", None) is not None:
        return

    perms = {p.name for p in getattr(user.role, "permissions", [])} if (user.role and hasattr(user.role, "permissions")) else set()
    if "platform:observability:view" in perms or "platform:admin:view" in perms:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden: Observability access requires an active workspace or administrator role."
    )


@router.get("/overview", response_model=ObservabilityOverviewResponse)
def get_observability_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns aggregated real-time observability overview including request rates,
    p95 latency, active operational alerts, worker counts, and queue depths.
    """
    _validate_observability_access(current_user)

    # Evaluate rules
    operational_alert_engine.evaluate_rules(metrics=metrics_registry, db=db)

    req_metrics = metrics_registry.get_request_metrics()
    infra_metrics = metrics_registry.get_infrastructure_metrics()
    worker_metrics = infra_metrics.get("worker", {})
    alerts = operational_alert_engine.get_alerts()

    active_alerts = [a for a in alerts if a.status in ["TRIGGERED", "ACKNOWLEDGED"]]
    critical_alerts = [a for a in active_alerts if a.severity == "CRITICAL"]

    total_reqs = req_metrics.get("total_requests", 0)
    error_rate_pct = req_metrics.get("error_rate_percentage", 0.0)
    p95_lat = req_metrics.get("latency_ms", {}).get("p95", 0.0)

    # Determine overall system health
    if critical_alerts or error_rate_pct >= 10.0:
        sys_status = "unhealthy"
    elif active_alerts or error_rate_pct >= 2.0:
        sys_status = "degraded"
    else:
        sys_status = "healthy"

    return ObservabilityOverviewResponse(
        status=sys_status,
        total_requests=total_reqs,
        error_rate_percentage=error_rate_pct,
        latency_p95_ms=p95_lat,
        active_alerts=len(active_alerts),
        critical_alerts=len(critical_alerts),
        jobs_queued=worker_metrics.get("jobs_queued", 0),
        jobs_dead_lettered=worker_metrics.get("jobs_dead_lettered", 0),
    )


@router.get("/metrics/requests", response_model=RequestMetricsResponse)
def get_request_metrics(
    current_user: User = Depends(get_current_user),
):
    """
    Returns request latency percentiles (p50, p90, p95, p99), error rates,
    and HTTP status code breakdowns.
    """
    _validate_observability_access(current_user)
    return metrics_registry.get_request_metrics()


@router.get("/metrics/infrastructure", response_model=InfrastructureMetricsResponse)
def get_infrastructure_metrics(
    current_user: User = Depends(get_current_user),
):
    """
    Returns database connection pool utilization, Redis connectivity,
    queue depths, worker heartbeats, and scheduler cycles.
    """
    _validate_observability_access(current_user)
    return metrics_registry.get_infrastructure_metrics()


@router.get("/metrics/domains", response_model=DomainMetricsResponse)
def get_domain_metrics(
    current_user: User = Depends(get_current_user),
):
    """
    Returns execution telemetry across domain subsystems (MCP, RAG, Graph, Workflows, Intelligence, Agents).
    """
    _validate_observability_access(current_user)
    return metrics_registry.get_domain_telemetry()


@router.get("/alerts", response_model=OperationalAlertListResponse)
def list_operational_alerts(
    status_filter: Optional[str] = Query(None, description="Optional alert status filter: TRIGGERED, ACKNOWLEDGED, RESOLVED"),
    severity_filter: Optional[str] = Query(None, description="Optional alert severity filter: CRITICAL, WARNING, INFO"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists operational alerts with optional status and severity filtering.
    """
    _validate_observability_access(current_user)
    ws_raw = getattr(current_user, "workspace_id", None)
    ws_id = str(ws_raw) if ws_raw else None
    alerts = operational_alert_engine.get_alerts(
        status_filter=status_filter,
        severity_filter=severity_filter,
        workspace_id=ws_id
    )
    return OperationalAlertListResponse(total=len(alerts), alerts=alerts)


@router.post("/alerts/{alert_id}/acknowledge", response_model=OperationalAlertResponse)
def acknowledge_operational_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Acknowledges an active operational alert.
    """
    _validate_observability_access(current_user)
    actor_id = str(current_user.id)
    alert = operational_alert_engine.acknowledge_alert(alert_id, acknowledged_by=actor_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operational alert '{alert_id}' not found."
        )
    return alert


@router.post("/alerts/{alert_id}/resolve", response_model=OperationalAlertResponse)
def resolve_operational_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Resolves an operational alert.
    """
    _validate_observability_access(current_user)
    actor_id = str(current_user.id)
    alert = operational_alert_engine.resolve_alert(alert_id, resolved_by=actor_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operational alert '{alert_id}' not found."
        )
    return alert


@router.get("/incident/timeline", response_model=IncidentTimelineResponse)
def get_incident_timeline(
    query_id: str = Query(..., description="Target correlation ID, request ID, job ID, or execution ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Correlates incident timeline events across logs, background jobs, audit records,
    and operational alerts for a given correlation_id, request_id, or job_id.
    """
    _validate_observability_access(current_user)
    ws_raw = getattr(current_user, "workspace_id", None)
    ws_id = str(ws_raw) if ws_raw else None
    return operational_alert_engine.get_incident_timeline(query_id=query_id, db=db, workspace_id=ws_id)
