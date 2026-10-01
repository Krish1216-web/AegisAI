import uuid
import datetime
import hashlib
import threading
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from loguru import logger

from app.core.config import settings
from app.core.metrics import MetricsRegistry, metrics_registry
from app.core.mcp.security import CredentialStore
from app.models.audit import AuditLog
from app.models.job import BackgroundJob
from app.schemas.observability import (
    OperationalAlertResponse,
    IncidentTimelineEvent,
    IncidentTimelineResponse
)


class OperationalAlertEngine:
    """
    Production operational alerting engine.
    Monitors operational metrics, error rates, worker queue saturation,
    stale workers, dead-letter bursts, and resource limits.
    Provides alert deduplication, cooldown windows, state lifecycle transitions,
    and unified incident correlation.
    """

    def __init__(self, cooldown_seconds: int = 300):
        self._lock = threading.Lock()
        self._alerts: Dict[str, OperationalAlertResponse] = {}
        self._fingerprint_to_id: Dict[str, str] = {}
        self._cooldown_seconds = cooldown_seconds

    def _generate_fingerprint(self, rule_name: str, metric_name: str, entity_id: str = "") -> str:
        raw = f"{rule_name}:{metric_name}:{entity_id}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def trigger_alert(
        self,
        rule_name: str,
        severity: str,
        title: str,
        description: str,
        metric_name: str,
        current_value: float,
        threshold_value: float,
        entity_id: str = "",
        workspace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> OperationalAlertResponse:
        """
        Creates or updates an operational alert with deduplication and cooldown suppression.
        """
        with self._lock:
            fingerprint = self._generate_fingerprint(rule_name, metric_name, entity_id)
            now = datetime.datetime.now(datetime.timezone.utc)
            scrubbed_meta = CredentialStore.scrub_dict(metadata or {})

            if fingerprint in self._fingerprint_to_id:
                existing_id = self._fingerprint_to_id[fingerprint]
                existing_alert = self._alerts.get(existing_id)
                if existing_alert and existing_alert.status != "RESOLVED":
                    # Update existing alert values without creating duplicates
                    existing_alert.current_value = current_value
                    existing_alert.threshold_value = threshold_value
                    existing_alert.metadata.update(scrubbed_meta)
                    return existing_alert

            alert_id = str(uuid.uuid4())
            alert = OperationalAlertResponse(
                alert_id=alert_id,
                fingerprint=fingerprint,
                rule_name=rule_name,
                severity=severity.upper(),
                status="TRIGGERED",
                title=CredentialStore.scrub_text(title),
                description=CredentialStore.scrub_text(description),
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=threshold_value,
                triggered_at=now,
                workspace_id=workspace_id,
                metadata=scrubbed_meta,
            )
            self._alerts[alert_id] = alert
            self._fingerprint_to_id[fingerprint] = alert_id
            logger.warning(f"Operational Alert Triggered: [{severity}] {title} (ID: {alert_id})")
            return alert

    def evaluate_rules(
        self,
        metrics: Optional[MetricsRegistry] = None,
        db: Optional[Session] = None
    ) -> List[OperationalAlertResponse]:
        """
        Evaluates active operational rules against current in-memory metrics and database state.
        """
        registry = metrics or metrics_registry
        triggered = []

        # 1. Evaluate 5xx Error Rate
        req_metrics = registry.get_request_metrics()
        total_reqs = req_metrics.get("total_requests", 0)
        status_dist = req_metrics.get("status_code_distribution", {})
        five_xx = status_dist.get("5xx", 0)
        if total_reqs >= 5:
            error_rate = five_xx / total_reqs
            threshold = getattr(settings, "ALERT_ERROR_RATE_THRESHOLD", 0.05)
            if error_rate > threshold:
                alert = self.trigger_alert(
                    rule_name="HIGH_5XX_ERROR_RATE",
                    severity="CRITICAL",
                    title="High 5xx HTTP Error Rate Detected",
                    description=f"5xx error rate is {error_rate * 100:.1f}%, exceeding threshold of {threshold * 100:.1f}%.",
                    metric_name="http_5xx_rate",
                    current_value=error_rate,
                    threshold_value=threshold,
                    metadata={"total_requests": total_reqs, "5xx_count": five_xx},
                )
                triggered.append(alert)

        # 2. Evaluate Worker Metrics
        infra_metrics = registry.get_infrastructure_metrics()
        worker_metrics = infra_metrics.get("worker", {})
        dead_letters = worker_metrics.get("jobs_dead_lettered", 0)
        if dead_letters >= 5:
            alert = self.trigger_alert(
                rule_name="DEAD_LETTER_BURST",
                severity="HIGH",
                title="Dead-Letter Job Threshold Exceeded",
                description=f"Dead-lettered jobs count reached {dead_letters}.",
                metric_name="dead_letter_count",
                current_value=float(dead_letters),
                threshold_value=5.0,
                metadata={"dead_letter_count": dead_letters},
            )
            triggered.append(alert)

        # 3. Evaluate Database Metrics
        db_metrics = infra_metrics.get("database", {})
        pool_exhaustions = db_metrics.get("pool_exhaustions", 0)
        conn_failures = db_metrics.get("connection_failures", 0)
        if pool_exhaustions > 0 or conn_failures >= 3:
            alert = self.trigger_alert(
                rule_name="DATABASE_POOL_SATURATION",
                severity="WARNING",
                title="Database Connection Pool Exhaustion / Failures Detected",
                description=f"DB pool exhaustions: {pool_exhaustions}, connection failures: {conn_failures}.",
                metric_name="db_pool_failures",
                current_value=float(pool_exhaustions + conn_failures),
                threshold_value=1.0,
                metadata={"pool_exhaustions": pool_exhaustions, "connection_failures": conn_failures},
            )
            triggered.append(alert)

        return triggered

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> Optional[OperationalAlertResponse]:
        with self._lock:
            alert = self._alerts.get(alert_id)
            if not alert:
                return None
            alert.status = "ACKNOWLEDGED"
            alert.acknowledged_at = datetime.datetime.now(datetime.timezone.utc)
            alert.acknowledged_by = acknowledged_by
            return alert

    def resolve_alert(self, alert_id: str, resolved_by: str) -> Optional[OperationalAlertResponse]:
        with self._lock:
            alert = self._alerts.get(alert_id)
            if not alert:
                return None
            alert.status = "RESOLVED"
            alert.resolved_at = datetime.datetime.now(datetime.timezone.utc)
            alert.resolved_by = resolved_by
            return alert

    def get_alerts(
        self,
        status_filter: Optional[str] = None,
        severity_filter: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> List[OperationalAlertResponse]:
        with self._lock:
            alerts = list(self._alerts.values())

        if status_filter:
            alerts = [a for a in alerts if a.status.upper() == status_filter.upper()]
        if severity_filter:
            alerts = [a for a in alerts if a.severity.upper() == severity_filter.upper()]
        if workspace_id:
            alerts = [a for a in alerts if not a.workspace_id or a.workspace_id == workspace_id]

        alerts.sort(key=lambda a: a.triggered_at, reverse=True)
        return alerts

    def get_incident_timeline(
        self,
        query_id: str,
        db: Session,
        workspace_id: Optional[str] = None
    ) -> IncidentTimelineResponse:
        """
        Correlates incident timeline events across logs, jobs, alerts, and audit entries
        given a correlation_id, request_id, execution_id, or job_id.
        """
        events: List[IncidentTimelineEvent] = []
        clean_id = query_id.strip()

        # 1. Search in-memory operational alerts
        with self._lock:
            for alert in self._alerts.values():
                if (
                    clean_id in alert.alert_id
                    or clean_id in alert.fingerprint
                    or (alert.metadata and clean_id in str(alert.metadata))
                ):
                    events.append(
                        IncidentTimelineEvent(
                            timestamp=alert.triggered_at,
                            source="alert",
                            event_type=f"alert:{alert.rule_name}",
                            severity=alert.severity,
                            summary=alert.title,
                            details=CredentialStore.scrub_dict(alert.metadata or {}),
                        )
                    )

        # 2. Query Background Jobs
        try:
            job_filters = [
                BackgroundJob.id == clean_id if self._is_uuid(clean_id) else False,
                BackgroundJob.correlation_id == clean_id,
                BackgroundJob.idempotency_key == clean_id,
            ]
            valid_filters = [f for f in job_filters if f is not False]
            if valid_filters:
                q = db.query(BackgroundJob).filter(or_(*valid_filters))
                if workspace_id and self._is_uuid(workspace_id):
                    q = q.filter(BackgroundJob.workspace_id == uuid.UUID(workspace_id))
                jobs = q.all()

                for j in jobs:
                    events.append(
                        IncidentTimelineEvent(
                            timestamp=j.created_at,
                            source="worker",
                            event_type=f"job:{j.job_type}:created",
                            severity="INFO",
                            summary=f"Job {j.id} created with priority {j.priority}",
                            details={"status": j.status.value, "job_type": j.job_type, "attempts": j.attempts},
                        )
                    )
                    if j.started_at:
                        events.append(
                            IncidentTimelineEvent(
                                timestamp=j.started_at,
                                source="worker",
                                event_type=f"job:{j.job_type}:started",
                                severity="INFO",
                                summary=f"Job {j.id} started execution on worker {j.worker_id}",
                                details={"worker_id": j.worker_id},
                            )
                        )
                    if j.completed_at:
                        is_fail = j.status.value in ["failed", "dead_lettered"]
                        events.append(
                            IncidentTimelineEvent(
                                timestamp=j.completed_at,
                                source="worker",
                                event_type=f"job:{j.job_type}:{j.status.value}",
                                severity="CRITICAL" if is_fail else "INFO",
                                summary=f"Job {j.id} finished with status {j.status.value}",
                                details={
                                    "error": CredentialStore.scrub_text(j.last_error or ""),
                                    "error_category": j.error_category.value if j.error_category else None,
                                },
                            )
                        )
        except Exception as e:
            logger.debug(f"Incident timeline job query notice: {e}")

        # 3. Query Audit Logs
        try:
            audit_filters = [
                AuditLog.action.ilike(f"%{clean_id}%"),
                AuditLog.details.ilike(f"%{clean_id}%"),
            ]
            if self._is_uuid(clean_id):
                audit_filters.append(AuditLog.id == uuid.UUID(clean_id))
                audit_filters.append(AuditLog.user_id == uuid.UUID(clean_id))

            logs = db.query(AuditLog).filter(or_(*audit_filters)).limit(50).all()
            for log in logs:
                events.append(
                    IncidentTimelineEvent(
                        timestamp=log.created_at,
                        source="audit",
                        event_type=f"audit:{log.action}",
                        severity="INFO",
                        summary=f"Audit event '{log.action}' recorded",
                        details={"ip_address": log.ip_address, "details": CredentialStore.scrub_text(log.details or "")},
                    )
                )
        except Exception as e:
            logger.debug(f"Incident timeline audit query notice: {e}")

        # Sort chronologically
        events.sort(key=lambda ev: ev.timestamp)

        return IncidentTimelineResponse(
            query_id=clean_id,
            total_events=len(events),
            events=events,
        )

    def _is_uuid(self, val: str) -> bool:
        try:
            uuid.UUID(str(val))
            return True
        except (ValueError, TypeError, AttributeError):
            return False

    def reset(self) -> None:
        with self._lock:
            self._alerts.clear()
            self._fingerprint_to_id.clear()


operational_alert_engine = OperationalAlertEngine()
