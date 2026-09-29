import uuid
import datetime
import threading
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, deque
from sqlalchemy.orm import Session
from loguru import logger

from app.core.security_events import (
    SecurityEventType,
    SecuritySeverity,
    SecurityEventRecord,
    DEFAULT_SEVERITY_MAP
)
from app.core.platform.events import (
    PlatformEventType,
    PlatformEvent,
    PlatformEventDispatcher
)
from app.core.platform.lifecycle import LifecycleState
from app.core.mcp.security import CredentialStore
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.security_observability import (
    SecurityEventItem,
    SecurityEventListResponse,
    SecurityAlertItem,
    SecurityAlertListResponse,
    SecurityMetricsResponse,
    IncidentEvidenceTimelineItem,
    IncidentEvidenceResponse,
    AuditIntegrityResponse,
    RetentionPolicyResponse
)

MAX_IN_MEMORY_SECURITY_EVENTS = 5000
ALERT_COOLDOWN_SECONDS = 300 # 5-minute cooldown window for deduplicating alerts

class SecurityAlertEngine:
    """
    Real-time pattern evaluation engine for detecting security anomalies,
    brute-force attacks, SSRF, prompt injections, and privilege violations.
    Includes alert storm suppression and deduplication.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._alerts: Dict[str, SecurityAlertItem] = {} # alert_id -> alert
        self._cooldowns: Dict[str, str] = {} # cooldown_key -> alert_id
        self._auth_failure_tracker: Dict[str, deque] = defaultdict(lambda: deque(maxlen=20)) # actor/ip -> timestamps
        self._authz_denial_tracker: Dict[str, deque] = defaultdict(lambda: deque(maxlen=20))

    def evaluate_event(self, event: SecurityEventRecord) -> Optional[SecurityAlertItem]:
        with self._lock:
            alert_to_emit = None
            now = event.timestamp

            actor_key = str(event.actor_id) if event.actor_id else (event.source_ip or "unknown")

            # Rule 1: Repeated Authentication Failures (>= 5 in 10 mins)
            if event.event_type == SecurityEventType.AUTH_LOGIN_FAILED:
                self._auth_failure_tracker[actor_key].append(now)
                recent_fails = [t for t in self._auth_failure_tracker[actor_key] if (now - t).total_seconds() <= 600]
                if len(recent_fails) >= 5:
                    alert_to_emit = self._create_or_update_alert(
                        rule_name="REPEATED_AUTH_FAILURES",
                        title="Multiple Authentication Failures Detected",
                        description=f"Actor '{actor_key}' incurred {len(recent_fails)} login failures within 10 minutes.",
                        severity=SecuritySeverity.HIGH,
                        workspace_id=event.workspace_id,
                        actor_id=event.actor_id,
                        correlation_id=event.correlation_id,
                        execution_id=event.execution_id,
                        metadata={"recent_failure_count": len(recent_fails), "source_ip": event.source_ip}
                    )

            # Rule 2: Refresh Token Replay Detected
            elif event.event_type == SecurityEventType.AUTH_REFRESH_REPLAY:
                alert_to_emit = self._create_or_update_alert(
                    rule_name="REFRESH_TOKEN_REPLAY",
                    title="Critical Token Replay Attack Detected",
                    description=f"Attempted reuse of already rotated refresh token for user {event.actor_id}.",
                    severity=SecuritySeverity.CRITICAL,
                    workspace_id=event.workspace_id,
                    actor_id=event.actor_id,
                    correlation_id=event.correlation_id,
                    metadata={"details": event.sanitized_details}
                )

            # Rule 3: Cross-Tenant Boundary Violation / IDOR
            elif event.event_type in (SecurityEventType.TENANT_BOUNDARY_VIOLATION, SecurityEventType.IDOR_ATTEMPT, SecurityEventType.BOLA_ATTEMPT):
                alert_to_emit = self._create_or_update_alert(
                    rule_name="TENANT_BOUNDARY_VIOLATION",
                    title="Cross-Tenant Access Boundary Violation",
                    description=f"Unauthorized access attempt crossing workspace boundaries by actor {event.actor_id}.",
                    severity=SecuritySeverity.HIGH,
                    workspace_id=event.workspace_id,
                    actor_id=event.actor_id,
                    correlation_id=event.correlation_id,
                    metadata={"action": event.action, "reason": event.reason}
                )

            # Rule 4: SSRF Outbound Block
            elif event.event_type == SecurityEventType.SSRF_BLOCKED:
                alert_to_emit = self._create_or_update_alert(
                    rule_name="SSRF_ATTEMPT",
                    title="Server-Side Request Forgery (SSRF) Blocked",
                    description=f"Forbidden private / internal IP connection attempted: {event.reason}",
                    severity=SecuritySeverity.HIGH,
                    workspace_id=event.workspace_id,
                    actor_id=event.actor_id,
                    correlation_id=event.correlation_id,
                    metadata=event.security_metadata
                )

            # Rule 5: Prompt Injection Block
            elif event.event_type == SecurityEventType.PROMPT_INJECTION_BLOCKED:
                alert_to_emit = self._create_or_update_alert(
                    rule_name="PROMPT_INJECTION_BLOCKED",
                    title="Adversarial Prompt Injection Blocked",
                    description=f"Direct or document-based prompt injection pattern intercepted: {event.reason}",
                    severity=SecuritySeverity.HIGH,
                    workspace_id=event.workspace_id,
                    actor_id=event.actor_id,
                    correlation_id=event.correlation_id,
                    metadata=event.security_metadata
                )

            # Rule 6: MCP Restricted Tool / Policy Violation
            elif event.event_type in (SecurityEventType.MCP_SECURITY_VIOLATION, SecurityEventType.MCP_RESTRICTED_TOOL_ATTEMPT):
                alert_to_emit = self._create_or_update_alert(
                    rule_name="MCP_SECURITY_VIOLATION",
                    title="MCP Tool Security Policy Violation",
                    description=f"Unauthorized or restricted MCP execution attempt: {event.action} - {event.reason}",
                    severity=SecuritySeverity.HIGH,
                    workspace_id=event.workspace_id,
                    actor_id=event.actor_id,
                    correlation_id=event.correlation_id,
                    metadata=event.sanitized_details
                )

            # Rule 7: Rate Limit Abuse
            elif event.event_type == SecurityEventType.RATE_LIMIT_ABUSE:
                alert_to_emit = self._create_or_update_alert(
                    rule_name="RATE_LIMIT_ABUSE",
                    title="Aggressive API Rate Limit Abuse Detected",
                    description=f"Threshold exceeded repeatedly by actor {actor_key}.",
                    severity=SecuritySeverity.MEDIUM,
                    workspace_id=event.workspace_id,
                    actor_id=event.actor_id,
                    correlation_id=event.correlation_id,
                    metadata={"source_ip": event.source_ip}
                )

            # Rule 8: Repeated Authorization Denials (>= 5 in 10 mins)
            elif event.event_type == SecurityEventType.AUTHZ_DENIED:
                self._authz_denial_tracker[actor_key].append(now)
                recent_denials = [t for t in self._authz_denial_tracker[actor_key] if (now - t).total_seconds() <= 600]
                if len(recent_denials) >= 5:
                    alert_to_emit = self._create_or_update_alert(
                        rule_name="REPEATED_AUTHZ_DENIALS",
                        title="Multiple Authorization Denials Detected",
                        description=f"Actor '{actor_key}' triggered {len(recent_denials)} permission denials within 10 minutes.",
                        severity=SecuritySeverity.HIGH,
                        workspace_id=event.workspace_id,
                        actor_id=event.actor_id,
                        correlation_id=event.correlation_id,
                        metadata={"recent_denial_count": len(recent_denials)}
                    )

            # Rule 9: Suspicious Admin Action / Privilege Anomaly
            elif event.event_type == SecurityEventType.ADMIN_SUSPENSION_ACTION:
                alert_to_emit = self._create_or_update_alert(
                    rule_name="ADMIN_USER_SUSPENSION",
                    title="Administrative Account Suspension Executed",
                    description=f"Admin {event.actor_id} suspended user account. Reason: {event.reason}",
                    severity=SecuritySeverity.HIGH,
                    workspace_id=event.workspace_id,
                    actor_id=event.actor_id,
                    correlation_id=event.correlation_id,
                    metadata=event.sanitized_details
                )

            return alert_to_emit

    def _create_or_update_alert(
        self,
        rule_name: str,
        title: str,
        description: str,
        severity: SecuritySeverity,
        workspace_id: Optional[uuid.UUID],
        actor_id: Optional[uuid.UUID],
        correlation_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SecurityAlertItem:
        cooldown_key = f"{rule_name}:{workspace_id}:{actor_id}"
        now = datetime.datetime.now(datetime.timezone.utc)

        if cooldown_key in self._cooldowns:
            alert_id = self._cooldowns[cooldown_key]
            existing_alert = self._alerts.get(alert_id)
            if existing_alert and (now - existing_alert.last_triggered_at).total_seconds() <= ALERT_COOLDOWN_SECONDS:
                # Deduplicate: update trigger count and last timestamp
                existing_alert.trigger_count += 1
                existing_alert.last_triggered_at = now
                existing_alert.metadata.update(metadata or {})
                return existing_alert

        # Create fresh alert
        alert_id = f"alt_{uuid.uuid4().hex[:12]}"
        alert = SecurityAlertItem(
            alert_id=alert_id,
            rule_name=rule_name,
            title=title,
            description=CredentialStore.redact_sensitive_str(description),
            severity=severity,
            status="ACTIVE",
            workspace_id=workspace_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            execution_id=execution_id,
            trigger_count=1,
            first_triggered_at=now,
            last_triggered_at=now,
            metadata=CredentialStore.redact_sensitive_dict(metadata or {})
        )
        self._alerts[alert_id] = alert
        self._cooldowns[cooldown_key] = alert_id
        return alert

    def get_alerts(
        self,
        workspace_id: Optional[uuid.UUID] = None,
        severity: Optional[SecuritySeverity] = None,
        status_filter: Optional[str] = None
    ) -> List[SecurityAlertItem]:
        with self._lock:
            alerts = list(self._alerts.values())

        filtered = []
        for a in alerts:
            if workspace_id and a.workspace_id and a.workspace_id != workspace_id:
                continue
            if severity and a.severity != severity:
                continue
            if status_filter and a.status != status_filter:
                continue
            filtered.append(a)

        return sorted(filtered, key=lambda a: a.last_triggered_at, reverse=True)


class SecurityObservabilityService:
    """
    Centralized Security Observability, Cryptographic Audit Trail,
    Incident Evidence Correlator, and Compliance Readiness Service for AegisAI.
    """
    _lock = threading.Lock()
    _events: deque = deque(maxlen=MAX_IN_MEMORY_SECURITY_EVENTS)
    _latest_hash: Optional[str] = "GENESIS_HASH"
    alert_engine = SecurityAlertEngine()

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def record_event(
        self,
        event_type: SecurityEventType,
        source_component: str,
        action: str,
        outcome: str = "SUCCESS",
        actor_id: Optional[uuid.UUID] = None,
        workspace_id: Optional[uuid.UUID] = None,
        team_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        severity: Optional[SecuritySeverity] = None,
        reason: Optional[str] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        security_metadata: Optional[Dict[str, Any]] = None,
        sanitized_details: Optional[Dict[str, Any]] = None,
        persist_to_audit_log: bool = True
    ) -> SecurityEventRecord:
        """
        Records a canonical security event, cryptographically links it to the chain,
        evaluates alerting rules, and emits unified platform events.
        """
        sev = severity or DEFAULT_SEVERITY_MAP.get(event_type, SecuritySeverity.INFO)

        event = SecurityEventRecord(
            event_type=event_type,
            severity=sev,
            actor_id=actor_id,
            workspace_id=workspace_id,
            team_id=team_id,
            project_id=project_id,
            request_id=request_id,
            correlation_id=correlation_id,
            execution_id=execution_id,
            source_component=source_component,
            action=action,
            outcome=outcome,
            reason=reason,
            source_ip=source_ip,
            user_agent=user_agent,
            security_metadata=security_metadata or {},
            sanitized_details=sanitized_details or {}
        )

        with self._lock:
            # Cryptographic chain linkage
            prev_hash = self._latest_hash or "GENESIS_HASH"
            event.compute_hash(previous_hash=prev_hash)
            self._latest_hash = event.event_hash
            self._events.append(event)

        # Evaluate real-time security alerts
        self.alert_engine.evaluate_event(event)

        # Dispatch via PlatformEventDispatcher
        try:
            platform_evt = PlatformEvent(
                event_id=event.event_id,
                event_type=PlatformEventType.SECURITY_EVENT,
                timestamp=event.timestamp,
                correlation_id=event.correlation_id or event.event_id,
                workspace_id=event.workspace_id or uuid.uuid4(),
                user_id=event.actor_id,
                source_component=event.source_component,
                payload={
                    "security_event_type": event.event_type.value,
                    "severity": event.severity.value,
                    "action": event.action,
                    "outcome": event.outcome,
                    "reason": event.reason,
                    "event_hash": event.event_hash
                }
            )
            PlatformEventDispatcher.emit(platform_evt)
        except Exception as pe_err:
            logger.debug(f"PlatformEvent emission ignored: {pe_err}")

        # Persist to database AuditLog if DB session available
        if persist_to_audit_log and self.db:
            try:
                import json
                audit_entry = AuditLog(
                    id=uuid.uuid4(),
                    user_id=event.actor_id,
                    action=f"SEC:{event.event_type.value}:{event.action}",
                    ip_address=event.source_ip,
                    details=json.dumps({
                        "event_id": event.event_id,
                        "workspace_id": str(event.workspace_id) if event.workspace_id else None,
                        "severity": event.severity.value,
                        "outcome": event.outcome,
                        "reason": event.reason,
                        "correlation_id": event.correlation_id,
                        "execution_id": event.execution_id,
                        "event_hash": event.event_hash,
                        "previous_hash": event.previous_hash
                    })
                )
                self.db.add(audit_entry)
                self.db.commit()
            except Exception as db_err:
                logger.debug(f"AuditLog DB insertion skipped: {db_err}")
                try:
                    self.db.rollback()
                except Exception:
                    pass

        return event

    def list_events(
        self,
        page: int = 1,
        page_size: int = 20,
        workspace_id: Optional[uuid.UUID] = None,
        severity: Optional[SecuritySeverity] = None,
        event_type: Optional[SecurityEventType] = None,
        search: Optional[str] = None,
        since_dt: Optional[datetime.datetime] = None
    ) -> SecurityEventListResponse:
        with self._lock:
            all_events = list(self._events)

        filtered = []
        for e in all_events:
            # Tenant isolation
            if workspace_id and e.workspace_id and e.workspace_id != workspace_id:
                continue
            if severity and e.severity != severity:
                continue
            if event_type and e.event_type != event_type:
                continue
            if since_dt and e.timestamp < since_dt:
                continue
            if search:
                s_lower = search.lower()
                matches = (
                    s_lower in e.action.lower() or
                    (e.reason and s_lower in e.reason.lower()) or
                    (e.correlation_id and s_lower in e.correlation_id.lower()) or
                    (e.execution_id and s_lower in e.execution_id.lower()) or
                    s_lower in e.event_type.value.lower()
                )
                if not matches:
                    continue
            filtered.append(e)

        # Sort newest first
        filtered.sort(key=lambda x: x.timestamp, reverse=True)
        total = len(filtered)
        offset = max(0, (page - 1) * page_size)
        paginated = filtered[offset:offset + page_size]

        items = [
            SecurityEventItem(
                event_id=e.event_id,
                event_type=e.event_type,
                timestamp=e.timestamp,
                severity=e.severity,
                actor_id=e.actor_id,
                workspace_id=e.workspace_id,
                team_id=e.team_id,
                project_id=e.project_id,
                request_id=e.request_id,
                correlation_id=e.correlation_id,
                execution_id=e.execution_id,
                source_component=e.source_component,
                action=e.action,
                outcome=e.outcome,
                reason=e.reason,
                source_ip=e.source_ip,
                user_agent=e.user_agent,
                security_metadata=e.security_metadata,
                sanitized_details=e.sanitized_details,
                event_hash=e.event_hash,
                previous_hash=e.previous_hash
            )
            for e in paginated
        ]

        return SecurityEventListResponse(
            total=total,
            page=page,
            page_size=page_size,
            events=items
        )

    def verify_integrity(self, workspace_id: Optional[uuid.UUID] = None) -> AuditIntegrityResponse:
        """
        Traverses the security event audit chain and verifies cryptographic SHA-256 integrity.
        Detects any modified fields, dropped events, or broken previous_hash links.
        """
        with self._lock:
            all_events = list(self._events)

        if workspace_id:
            events_to_verify = [e for e in all_events if e.workspace_id == workspace_id]
        else:
            events_to_verify = all_events

        is_valid = True
        tampered_ids: List[str] = []
        broken_links = 0
        current_expected_prev = "GENESIS_HASH"

        for i, ev in enumerate(events_to_verify):
            # 1. Verify previous_hash linkage
            if ev.previous_hash != current_expected_prev and i > 0 and not workspace_id:
                broken_links += 1
                is_valid = False
                tampered_ids.append(ev.event_id)

            # 2. Recalculate hash
            import hashlib
            hasher = hashlib.sha256()
            hasher.update(ev.canonical_bytes())
            recalculated = hasher.hexdigest()

            if recalculated != ev.event_hash:
                is_valid = False
                tampered_ids.append(ev.event_id)

            current_expected_prev = ev.event_hash

        return AuditIntegrityResponse(
            is_valid=is_valid,
            total_events_verified=len(events_to_verify),
            tampered_events_count=len(tampered_ids),
            broken_links_count=broken_links,
            tampered_event_ids=tampered_ids,
            latest_chain_hash=self._latest_hash
        )

    def get_security_metrics(
        self,
        workspace_id: Optional[uuid.UUID] = None,
        time_window: str = "24h"
    ) -> SecurityMetricsResponse:
        """
        Computes deterministic security metrics over bounded time windows.
        """
        delta = datetime.timedelta(hours=24)
        if time_window == "1h":
            delta = datetime.timedelta(hours=1)
        elif time_window == "7d":
            delta = datetime.timedelta(days=7)
        elif time_window == "30d":
            delta = datetime.timedelta(days=30)

        since_dt = datetime.datetime.now(datetime.timezone.utc) - delta

        with self._lock:
            events = [
                e for e in self._events
                if (not workspace_id or not e.workspace_id or e.workspace_id == workspace_id)
                and e.timestamp >= since_dt
            ]

        sev_counts = {s.value: 0 for s in SecuritySeverity}
        cat_counts: Dict[str, int] = defaultdict(int)
        auth_metrics = {"login_success": 0, "login_failed": 0, "token_rotated": 0, "refresh_replay": 0}
        authz_metrics = {"authz_denied": 0, "tenant_boundary_violation": 0, "idor_attempt": 0}
        ai_mcp_metrics = {"ssrf_blocked": 0, "prompt_injection_blocked": 0, "mcp_violations": 0}

        for ev in events:
            sev_counts[ev.severity.value] += 1
            cat = ev.event_type.value.split("_")[0]
            cat_counts[cat] += 1

            # Auth
            if ev.event_type == SecurityEventType.AUTH_LOGIN_SUCCESS:
                auth_metrics["login_success"] += 1
            elif ev.event_type == SecurityEventType.AUTH_LOGIN_FAILED:
                auth_metrics["login_failed"] += 1
            elif ev.event_type == SecurityEventType.AUTH_TOKEN_ROTATED:
                auth_metrics["token_rotated"] += 1
            elif ev.event_type == SecurityEventType.AUTH_REFRESH_REPLAY:
                auth_metrics["refresh_replay"] += 1

            # Authz
            elif ev.event_type == SecurityEventType.AUTHZ_DENIED:
                authz_metrics["authz_denied"] += 1
            elif ev.event_type == SecurityEventType.TENANT_BOUNDARY_VIOLATION:
                authz_metrics["tenant_boundary_violation"] += 1
            elif ev.event_type in (SecurityEventType.IDOR_ATTEMPT, SecurityEventType.BOLA_ATTEMPT):
                authz_metrics["idor_attempt"] += 1

            # AI & MCP
            elif ev.event_type == SecurityEventType.SSRF_BLOCKED:
                ai_mcp_metrics["ssrf_blocked"] += 1
            elif ev.event_type == SecurityEventType.PROMPT_INJECTION_BLOCKED:
                ai_mcp_metrics["prompt_injection_blocked"] += 1
            elif ev.event_type in (SecurityEventType.MCP_SECURITY_VIOLATION, SecurityEventType.MCP_RESTRICTED_TOOL_ATTEMPT):
                ai_mcp_metrics["mcp_violations"] += 1

        # Alerts
        active_alerts = self.alert_engine.get_alerts(workspace_id=workspace_id, status_filter="ACTIVE")
        alert_sev_counts = {s.value: 0 for s in SecuritySeverity}
        for a in active_alerts:
            alert_sev_counts[a.severity.value] += 1

        recent_incidents = [
            {
                "alert_id": a.alert_id,
                "title": a.title,
                "severity": a.severity.value,
                "rule_name": a.rule_name,
                "last_triggered_at": a.last_triggered_at.isoformat(),
                "trigger_count": a.trigger_count
            }
            for a in active_alerts[:5]
        ]

        return SecurityMetricsResponse(
            time_window=time_window,
            total_events=len(events),
            events_by_severity=sev_counts,
            events_by_category=dict(cat_counts),
            authentication_metrics=auth_metrics,
            authorization_metrics=authz_metrics,
            ai_mcp_security_metrics=ai_mcp_metrics,
            total_active_alerts=len(active_alerts),
            alerts_by_severity=alert_sev_counts,
            recent_suspicious_incidents=recent_incidents
        )

    def lookup_incident_evidence(
        self,
        query_param: str,
        query_value: str,
        workspace_id: Optional[uuid.UUID] = None
    ) -> IncidentEvidenceResponse:
        """
        Cross-system incident investigation: correlates User -> Request -> Security Events ->
        Execution -> Agent/MCP/RAG -> Results -> Audit Log into a unified evidence timeline.
        """
        timeline: List[IncidentEvidenceTimelineItem] = []
        found_actor: Optional[uuid.UUID] = None
        found_ws: Optional[uuid.UUID] = workspace_id
        found_corr: Optional[str] = None
        found_exec: Optional[str] = None
        found_req: Optional[str] = None

        with self._lock:
            all_events = list(self._events)

        # 1. Match Security Events
        for e in all_events:
            if workspace_id and e.workspace_id and e.workspace_id != workspace_id:
                continue

            matched = False
            if query_param == "correlation_id" and e.correlation_id == query_value:
                matched = True
            elif query_param == "execution_id" and e.execution_id == query_value:
                matched = True
            elif query_param == "request_id" and e.request_id == query_value:
                matched = True
            elif query_param == "actor_id" and str(e.actor_id) == query_value:
                matched = True
            elif query_param == "event_id" and e.event_id == query_value:
                matched = True

            if matched:
                if e.actor_id:
                    found_actor = e.actor_id
                if e.workspace_id:
                    found_ws = e.workspace_id
                if e.correlation_id:
                    found_corr = e.correlation_id
                if e.execution_id:
                    found_exec = e.execution_id
                if e.request_id:
                    found_req = e.request_id

                timeline.append(
                    IncidentEvidenceTimelineItem(
                        timestamp=e.timestamp,
                        component=e.source_component,
                        event_type=f"SECURITY:{e.event_type.value}",
                        identifier=e.event_id,
                        summary=f"[{e.severity.value}] {e.action} -> {e.outcome} ({e.reason or 'OK'})",
                        details={
                            "action": e.action,
                            "outcome": e.outcome,
                            "reason": e.reason,
                            "source_ip": e.source_ip,
                            "security_metadata": e.security_metadata,
                            "sanitized_details": e.sanitized_details,
                            "event_hash": e.event_hash
                        }
                    )
                )

        # 2. Match Platform Executions
        from app.services.platform_execution import PlatformExecutionService
        all_execs = list(PlatformExecutionService._executions.values())
        for ex in all_execs:
            ex_ws = ex.metadata.get("workspace_id")
            if workspace_id and ex_ws and str(ex_ws) != str(workspace_id):
                continue

            matched_exec = False
            if query_param == "execution_id" and ex.execution_id == query_value:
                matched_exec = True
            elif query_param == "correlation_id" and ex.correlation_id == query_value:
                matched_exec = True
            elif found_exec and ex.execution_id == found_exec:
                matched_exec = True
            elif found_corr and ex.correlation_id == found_corr:
                matched_exec = True

            if matched_exec:
                timeline.append(
                    IncidentEvidenceTimelineItem(
                        timestamp=ex.started_at,
                        component="PlatformExecutionService",
                        event_type=f"EXECUTION:{ex.status.value.upper()}",
                        identifier=ex.execution_id,
                        summary=f"Capability '{ex.capability_id}' executed with status {ex.status.value} ({ex.duration_ms:.1f}ms)",
                        details={
                            "capability_id": ex.capability_id,
                            "status": ex.status.value,
                            "duration_ms": ex.duration_ms,
                            "errors": ex.errors,
                            "warnings": ex.warnings,
                            "provenance_count": len(ex.provenance)
                        }
                    )
                )

        # 3. Match DB Audit Logs if DB session available
        if self.db:
            try:
                db_logs = self.db.query(AuditLog).all()
                for al in db_logs:
                    matched_al = False
                    if query_param == "actor_id" and str(al.user_id) == query_value:
                        matched_al = True
                    elif al.details and query_value in al.details:
                        matched_al = True

                    if matched_al:
                        clean_det = CredentialStore.redact_sensitive_str(al.details or "")
                        timeline.append(
                            IncidentEvidenceTimelineItem(
                                timestamp=al.created_at,
                                component="AuditTrail",
                                event_type="AUDIT_LOG",
                                identifier=str(al.id),
                                summary=f"Audit action: {al.action} (IP: {al.ip_address or 'N/A'})",
                                details={"action": al.action, "ip_address": al.ip_address, "details": clean_det}
                            )
                        )
            except Exception as e:
                logger.debug(f"DB audit log search skipped: {e}")

        # Sort timeline chronologically
        def _normalize_dt(dt: Optional[datetime.datetime]) -> datetime.datetime:
            if dt is None:
                return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=datetime.timezone.utc)
            return dt

        timeline.sort(key=lambda x: _normalize_dt(x.timestamp))

        return IncidentEvidenceResponse(
            query_param=query_param,
            query_value=query_value,
            workspace_id=found_ws,
            actor_id=found_actor,
            correlation_id=found_corr,
            execution_id=found_exec,
            request_id=found_req,
            total_records_found=len(timeline),
            timeline=timeline
        )

    def inspect_retention(self, retention_days: int = 90) -> RetentionPolicyResponse:
        """
        Inspects records eligible for lifecycle archival/retention without deleting them (dry run).
        """
        threshold = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=retention_days)
        with self._lock:
            all_events = list(self._events)

        eligible = [e for e in all_events if e.timestamp < threshold]
        oldest = min([e.timestamp for e in all_events]) if all_events else None

        return RetentionPolicyResponse(
            retention_days_audit_logs=retention_days,
            retention_days_security_events=retention_days,
            retention_days_telemetry=30,
            eligible_records_count=len(eligible),
            oldest_record_timestamp=oldest,
            is_dry_run=True
        )

    def apply_retention(self, retention_days: int = 90, admin_user_id: Optional[uuid.UUID] = None) -> int:
        """
        Bounded, authorized lifecycle retention execution.
        Safely prunes in-memory events older than retention_days and logs an immutable audit event.
        """
        threshold = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=retention_days)
        purged_count = 0

        with self._lock:
            retained = deque([e for e in self._events if e.timestamp >= threshold], maxlen=MAX_IN_MEMORY_SECURITY_EVENTS)
            purged_count = len(self._events) - len(retained)
            self._events = retained

        # Record administrative retention audit event
        self.record_event(
            event_type=SecurityEventType.ADMIN_ACTION,
            source_component="SecurityRetentionLifecycle",
            action="APPLY_RETENTION_POLICY",
            outcome="SUCCESS",
            actor_id=admin_user_id,
            severity=SecuritySeverity.MEDIUM,
            reason=f"Executed data lifecycle retention policy: purged {purged_count} records older than {retention_days} days.",
            sanitized_details={"retention_days": retention_days, "purged_count": purged_count}
        )

        return purged_count

    @classmethod
    def clear(cls) -> None:
        """Testing utility to reset in-memory events and alerts."""
        with cls._lock:
            cls._events.clear()
            cls._latest_hash = "GENESIS_HASH"
            with cls.alert_engine._lock:
                cls.alert_engine._alerts.clear()
                cls.alert_engine._cooldowns.clear()
                cls.alert_engine._auth_failure_tracker.clear()
                cls.alert_engine._authz_denial_tracker.clear()
