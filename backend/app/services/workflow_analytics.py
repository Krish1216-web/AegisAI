import uuid
import datetime
import statistics
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc, asc

from app.models.workflow import (
    Workflow,
    WorkflowNode,
    WorkflowExecution,
    WorkflowExecutionNode,
    WorkflowSchedule,
    WorkflowApprovalRequest,
    WorkflowStatus,
    WorkflowExecutionStatus,
    WorkflowNodeStatus,
    WorkflowScheduleStatus,
    WorkflowApprovalStatus
)
from app.core.mcp.security import CredentialStore

class WorkflowAnalyticsService:
    """
    Deterministic Monitoring & Observability Service for AegisAI Workflows.
    Derives real-time, tenant-isolated execution metrics, performance timelines,
    node bottleneck analysis, failure clustering, and composition telemetry.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_overview_metrics(self, workspace_id: uuid.UUID, days: int = 7) -> Dict[str, Any]:
        """
        Computes high-level KPI overview metrics within bounded time window.
        """
        bounded_days = min(max(int(days), 1), 90)
        since_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=bounded_days)

        # 1. Workflows counts
        workflows = self.db.query(Workflow).filter(
            and_(
                Workflow.workspace_id == workspace_id,
                Workflow.deleted_at.is_(None)
            )
        ).all()
        total_workflows = len(workflows)
        active_workflows = sum(1 for w in workflows if w.status == WorkflowStatus.ACTIVE)
        paused_workflows = sum(1 for w in workflows if w.status == WorkflowStatus.PAUSED)
        archived_workflows = sum(1 for w in workflows if w.status == WorkflowStatus.ARCHIVED)

        # 2. Executions within window
        executions = self.db.query(WorkflowExecution).filter(
            and_(
                WorkflowExecution.workspace_id == workspace_id,
                WorkflowExecution.created_at >= since_dt,
                WorkflowExecution.deleted_at.is_(None)
            )
        ).all()

        total_executions = len(executions)
        running_executions = sum(1 for e in executions if e.status == WorkflowExecutionStatus.RUNNING)
        waiting_executions = sum(1 for e in executions if e.status == WorkflowExecutionStatus.WAITING)
        completed_executions = sum(1 for e in executions if e.status == WorkflowExecutionStatus.COMPLETED)
        failed_executions = sum(1 for e in executions if e.status == WorkflowExecutionStatus.FAILED)
        cancelled_executions = sum(1 for e in executions if e.status == WorkflowExecutionStatus.CANCELLED)

        terminal_count = completed_executions + failed_executions + cancelled_executions
        success_rate = round((completed_executions / terminal_count * 100), 1) if terminal_count > 0 else 0.0
        failure_rate = round((failed_executions / terminal_count * 100), 1) if terminal_count > 0 else 0.0
        cancellation_rate = round((cancelled_executions / terminal_count * 100), 1) if terminal_count > 0 else 0.0

        # Duration calculations (for completed executions with valid start and end)
        durations = []
        for e in executions:
            if e.started_at and e.completed_at and e.status == WorkflowExecutionStatus.COMPLETED:
                dur = (e.completed_at - e.started_at).total_seconds()
                if dur >= 0:
                    durations.append(dur)

        avg_duration = round(statistics.mean(durations), 2) if durations else 0.0
        median_duration = round(statistics.median(durations), 2) if durations else 0.0
        p95_duration = round(statistics.quantiles(durations, n=20)[18], 2) if len(durations) >= 20 else avg_duration

        # Time series by day
        day_map = defaultdict(lambda: {"executions": 0, "completed": 0, "failed": 0, "durations": []})
        for i in range(bounded_days):
            d = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            _ = day_map[d]  # prefill

        for e in executions:
            d_key = e.created_at.strftime("%Y-%m-%d")
            day_map[d_key]["executions"] += 1
            if e.status == WorkflowExecutionStatus.COMPLETED:
                day_map[d_key]["completed"] += 1
                if e.started_at and e.completed_at:
                    dur = (e.completed_at - e.started_at).total_seconds()
                    if dur >= 0:
                        day_map[d_key]["durations"].append(dur)
            elif e.status == WorkflowExecutionStatus.FAILED:
                day_map[d_key]["failed"] += 1

        time_series = []
        for d_key in sorted(day_map.keys()):
            d_data = day_map[d_key]
            d_avg = round(statistics.mean(d_data["durations"]), 2) if d_data["durations"] else 0.0
            time_series.append({
                "date": d_key,
                "executions": d_data["executions"],
                "completed": d_data["completed"],
                "failed": d_data["failed"],
                "avg_duration": d_avg
            })

        return {
            "window_days": bounded_days,
            "total_workflows": total_workflows,
            "active_workflows": active_workflows,
            "paused_workflows": paused_workflows,
            "archived_workflows": archived_workflows,
            "total_executions": total_executions,
            "running_executions": running_executions,
            "waiting_executions": waiting_executions,
            "completed_executions": completed_executions,
            "failed_executions": failed_executions,
            "cancelled_executions": cancelled_executions,
            "success_rate": success_rate,
            "failure_rate": failure_rate,
            "cancellation_rate": cancellation_rate,
            "avg_duration_seconds": avg_duration,
            "median_duration_seconds": median_duration,
            "p95_duration_seconds": p95_duration,
            "status_distribution": {
                "completed": completed_executions,
                "failed": failed_executions,
                "cancelled": cancelled_executions,
                "running": running_executions,
                "waiting": waiting_executions
            },
            "time_series": time_series
        }

    def get_workflow_performance(
        self,
        workspace_id: uuid.UUID,
        sort_by: str = "total_runs",
        order: str = "desc",
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Calculates per-workflow performance metrics and health scores.
        """
        bounded_limit = min(max(int(limit), 1), 100)
        bounded_offset = max(int(offset), 0)

        workflows = self.db.query(Workflow).filter(
            and_(
                Workflow.workspace_id == workspace_id,
                Workflow.deleted_at.is_(None)
            )
        ).all()

        results = []
        for w in workflows:
            execs = self.db.query(WorkflowExecution).filter(
                and_(
                    WorkflowExecution.workflow_id == w.id,
                    WorkflowExecution.workspace_id == workspace_id,
                    WorkflowExecution.deleted_at.is_(None)
                )
            ).order_by(desc(WorkflowExecution.created_at)).all()

            total_runs = len(execs)
            completed_runs = sum(1 for e in execs if e.status == WorkflowExecutionStatus.COMPLETED)
            failed_runs = sum(1 for e in execs if e.status == WorkflowExecutionStatus.FAILED)
            cancelled_runs = sum(1 for e in execs if e.status == WorkflowExecutionStatus.CANCELLED)

            terminal_count = completed_runs + failed_runs + cancelled_runs
            success_rate = round((completed_runs / terminal_count * 100), 1) if terminal_count > 0 else 0.0

            durations = []
            for e in execs:
                if e.started_at and e.completed_at and e.status == WorkflowExecutionStatus.COMPLETED:
                    dur = (e.completed_at - e.started_at).total_seconds()
                    if dur >= 0:
                        durations.append(dur)

            avg_dur = round(statistics.mean(durations), 2) if durations else 0.0
            min_dur = round(min(durations), 2) if durations else 0.0
            max_dur = round(max(durations), 2) if durations else 0.0

            latest_exec = execs[0] if execs else None
            latest_status = latest_exec.status.value if latest_exec else "none"
            latest_run_at = latest_exec.created_at.isoformat() if latest_exec else None

            # Health classification formula:
            # - HEALTHY: total_runs > 0, success_rate >= 85%, and latest_status != "failed"
            # - WARNING: success_rate between 50% and 85%, or (latest_status == "failed" and success_rate >= 50%)
            # - CRITICAL: total_runs > 0 and success_rate < 50%
            # - HEALTHY: 0 runs
            if total_runs == 0:
                health = "HEALTHY"
            elif success_rate < 50.0:
                health = "CRITICAL"
            elif success_rate < 85.0 or latest_status == "failed":
                health = "WARNING"
            else:
                health = "HEALTHY"

            results.append({
                "workflow_id": str(w.id),
                "workflow_name": w.name,
                "status": w.status.value,
                "version": w.version,
                "total_runs": total_runs,
                "completed_runs": completed_runs,
                "failed_runs": failed_runs,
                "cancelled_runs": cancelled_runs,
                "success_rate": success_rate,
                "avg_duration_seconds": avg_dur,
                "min_duration_seconds": min_dur,
                "max_duration_seconds": max_dur,
                "latest_run_at": latest_run_at,
                "latest_status": latest_status,
                "health": health
            })

        # Deterministic sorting
        is_reverse = (order.lower() == "desc")
        if sort_by == "success_rate":
            results.sort(key=lambda x: (x["success_rate"], x["total_runs"], x["workflow_name"]), reverse=is_reverse)
        elif sort_by == "avg_duration":
            results.sort(key=lambda x: (x["avg_duration_seconds"], x["total_runs"], x["workflow_name"]), reverse=is_reverse)
        elif sort_by == "failed_runs":
            results.sort(key=lambda x: (x["failed_runs"], x["workflow_name"]), reverse=is_reverse)
        else: # total_runs default
            results.sort(key=lambda x: (x["total_runs"], x["success_rate"], x["workflow_name"]), reverse=is_reverse)

        total_count = len(results)
        paginated_items = results[bounded_offset : bounded_offset + bounded_limit]

        return {
            "items": paginated_items,
            "total": total_count,
            "limit": bounded_limit,
            "offset": bounded_offset
        }

    def get_node_performance(
        self,
        workspace_id: uuid.UUID,
        workflow_id: Optional[uuid.UUID] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Analyzes per-node execution duration, failures, and identifies bottlenecks.
        """
        bounded_limit = min(max(int(limit), 1), 100)

        # Query all execution nodes for workspace
        query = self.db.query(WorkflowExecutionNode, WorkflowExecution.workflow_id).join(
            WorkflowExecution, WorkflowExecution.id == WorkflowExecutionNode.execution_id
        ).filter(
            and_(
                WorkflowExecution.workspace_id == workspace_id,
                WorkflowExecution.deleted_at.is_(None)
            )
        )

        if workflow_id:
            query = query.filter(WorkflowExecution.workflow_id == workflow_id)

        node_records = query.all()

        node_groups = defaultdict(lambda: {
            "node_key": "",
            "workflow_id": "",
            "executions": 0,
            "completed": 0,
            "failed": 0,
            "skipped": 0,
            "waiting": 0,
            "durations": []
        })

        for exec_node, wf_id in node_records:
            group_key = f"{wf_id}:{exec_node.node_key}"
            grp = node_groups[group_key]
            grp["node_key"] = exec_node.node_key
            grp["workflow_id"] = str(wf_id)
            grp["executions"] += 1

            if exec_node.status == WorkflowNodeStatus.COMPLETED:
                grp["completed"] += 1
                if exec_node.started_at and exec_node.completed_at:
                    dur = (exec_node.completed_at - exec_node.started_at).total_seconds()
                    if dur >= 0:
                        grp["durations"].append(dur)
            elif exec_node.status == WorkflowNodeStatus.FAILED:
                grp["failed"] += 1
            elif exec_node.status == WorkflowNodeStatus.SKIPPED:
                grp["skipped"] += 1
            elif exec_node.status == WorkflowNodeStatus.WAITING:
                grp["waiting"] += 1

        # Fetch workflow names
        wf_ids = {grp["workflow_id"] for grp in node_groups.values() if grp["workflow_id"]}
        wfs = self.db.query(Workflow).filter(Workflow.id.in_([uuid.UUID(w_id) for w_id in wf_ids])).all() if wf_ids else []
        wf_name_map = {str(w.id): w.name for w in wfs}

        items = []
        for group_key, grp in node_groups.items():
            total = grp["executions"]
            failed = grp["failed"]
            term = grp["completed"] + failed
            f_rate = round((failed / term * 100), 1) if term > 0 else 0.0
            durations = grp["durations"]
            avg_dur = round(statistics.mean(durations), 2) if durations else 0.0
            max_dur = round(max(durations), 2) if durations else 0.0

            # Bottleneck detection
            if f_rate >= 30.0:
                bottleneck = "HIGH_FAILURE"
            elif avg_dur >= 5.0:
                bottleneck = "SLOW"
            elif grp["waiting"] >= 5:
                bottleneck = "HIGH_WAIT"
            elif total >= 50:
                bottleneck = "HIGH_VOLUME"
            else:
                bottleneck = "NORMAL"

            items.append({
                "node_key": grp["node_key"],
                "workflow_id": grp["workflow_id"],
                "workflow_name": wf_name_map.get(grp["workflow_id"], "Unknown Workflow"),
                "total_executions": total,
                "completed_count": grp["completed"],
                "failed_count": failed,
                "skipped_count": grp["skipped"],
                "waiting_count": grp["waiting"],
                "avg_duration_seconds": avg_dur,
                "max_duration_seconds": max_dur,
                "failure_rate": f_rate,
                "bottleneck_category": bottleneck
            })

        # Sort by slowest / highest failure
        items.sort(key=lambda x: (x["avg_duration_seconds"], x["failure_rate"], x["total_executions"]), reverse=True)
        return {
            "items": items[:bounded_limit],
            "total": len(items)
        }

    def get_failure_analytics(self, workspace_id: uuid.UUID, limit: int = 50) -> Dict[str, Any]:
        """
        Clusters and sanitizes failure logs across workspace executions.
        """
        bounded_limit = min(max(int(limit), 1), 100)

        failed_nodes = self.db.query(WorkflowExecutionNode, WorkflowExecution.workflow_id).join(
            WorkflowExecution, WorkflowExecution.id == WorkflowExecutionNode.execution_id
        ).filter(
            and_(
                WorkflowExecution.workspace_id == workspace_id,
                WorkflowExecutionNode.status == WorkflowNodeStatus.FAILED,
                WorkflowExecution.deleted_at.is_(None)
            )
        ).order_by(desc(WorkflowExecutionNode.created_at)).all()

        cluster_map = defaultdict(lambda: {"count": 0, "latest_at": None, "wf_id": "", "node_key": "", "error": ""})

        for en, wf_id in failed_nodes:
            # Redact secrets
            raw_err = en.error or "Unknown Execution Error"
            clean_err = CredentialStore.redact_sensitive_str(raw_err)
            # Truncate clean_err for clustering
            clean_summary = clean_err[:200]

            key = f"{wf_id}:{en.node_key}:{clean_summary}"
            entry = cluster_map[key]
            entry["count"] += 1
            entry["wf_id"] = str(wf_id)
            entry["node_key"] = en.node_key
            entry["error"] = clean_summary
            if not entry["latest_at"] or (en.created_at and en.created_at > entry["latest_at"]):
                entry["latest_at"] = en.created_at

        # Fetch workflow names
        wf_ids = {entry["wf_id"] for entry in cluster_map.values() if entry["wf_id"]}
        wfs = self.db.query(Workflow).filter(Workflow.id.in_([uuid.UUID(w_id) for w_id in wf_ids])).all() if wf_ids else []
        wf_name_map = {str(w.id): w.name for w in wfs}

        items = []
        for entry in cluster_map.values():
            items.append({
                "workflow_id": entry["wf_id"],
                "workflow_name": wf_name_map.get(entry["wf_id"], "Unknown Workflow"),
                "node_key": entry["node_key"],
                "failure_count": entry["count"],
                "error_summary": entry["error"],
                "latest_failed_at": entry["latest_at"].isoformat() if entry["latest_at"] else None
            })

        items.sort(key=lambda x: (x["failure_count"], x["workflow_name"]), reverse=True)
        return {
            "items": items[:bounded_limit],
            "total": len(items)
        }

    def get_composition_analytics(self, workspace_id: uuid.UUID) -> Dict[str, Any]:
        """
        Analyzes sub-workflow nested executions, parallel branches, and merge policies.
        """
        exec_nodes = self.db.query(WorkflowExecutionNode).join(
            WorkflowExecution, WorkflowExecution.id == WorkflowExecutionNode.execution_id
        ).filter(
            and_(
                WorkflowExecution.workspace_id == workspace_id,
                WorkflowExecution.deleted_at.is_(None)
            )
        ).all()

        sub_wf_count = 0
        parallel_count = 0
        merge_count = 0
        merge_policy_dist = defaultdict(int)

        for en in exec_nodes:
            out = en.output_data or {}
            if isinstance(out, dict):
                if "_sub_execution_id" in out or "sub_execution_id" in out:
                    sub_wf_count += 1
                if out.get("parallel_fanout"):
                    parallel_count += 1
                if "policy" in out:
                    merge_count += 1
                    merge_policy_dist[out["policy"]] += 1

        return {
            "total_sub_workflow_invocations": sub_wf_count,
            "total_parallel_fanouts": parallel_count,
            "total_merge_fanins": merge_count,
            "merge_policy_distribution": dict(merge_policy_dist),
            "max_supported_nesting_depth": 3
        }

    def get_schedule_analytics(self, workspace_id: uuid.UUID) -> Dict[str, Any]:
        """
        Summarizes schedule execution performance.
        """
        schedules = self.db.query(WorkflowSchedule).filter(
            and_(
                WorkflowSchedule.workspace_id == workspace_id,
                WorkflowSchedule.deleted_at.is_(None)
            )
        ).all()

        total_schedules = len(schedules)
        active = sum(1 for s in schedules if s.status == WorkflowScheduleStatus.ACTIVE)
        paused = sum(1 for s in schedules if s.status == WorkflowScheduleStatus.PAUSED)
        completed = sum(1 for s in schedules if s.status == WorkflowScheduleStatus.COMPLETED)
        total_runs = sum(s.total_runs for s in schedules)
        total_failures = sum(s.failure_count for s in schedules)
        success_rate = round(((total_runs - total_failures) / total_runs * 100), 1) if total_runs > 0 else 100.0

        return {
            "total_schedules": total_schedules,
            "active_schedules": active,
            "paused_schedules": paused,
            "completed_schedules": completed,
            "total_scheduled_runs": total_runs,
            "total_scheduled_failures": total_failures,
            "scheduled_success_rate": success_rate
        }

    def get_approval_analytics(self, workspace_id: uuid.UUID) -> Dict[str, Any]:
        """
        Summarizes human approval turnaround times and approval rates.
        """
        approvals = self.db.query(WorkflowApprovalRequest).join(
            WorkflowExecution, WorkflowExecution.id == WorkflowApprovalRequest.execution_id
        ).filter(
            and_(
                WorkflowExecution.workspace_id == workspace_id,
                WorkflowApprovalRequest.deleted_at.is_(None)
            )
        ).all()

        total = len(approvals)
        pending = sum(1 for a in approvals if a.status == WorkflowApprovalStatus.PENDING)
        approved = sum(1 for a in approvals if a.status == WorkflowApprovalStatus.APPROVED)
        rejected = sum(1 for a in approvals if a.status == WorkflowApprovalStatus.REJECTED)
        expired = sum(1 for a in approvals if a.status == WorkflowApprovalStatus.EXPIRED)

        decided = approved + rejected
        approval_rate = round((approved / decided * 100), 1) if decided > 0 else 0.0

        turnaround_times = []
        for a in approvals:
            if a.created_at and a.decided_at and a.status in (WorkflowApprovalStatus.APPROVED, WorkflowApprovalStatus.REJECTED):
                dur = (a.decided_at - a.created_at).total_seconds()
                if dur >= 0:
                    turnaround_times.append(dur)

        avg_turnaround = round(statistics.mean(turnaround_times), 1) if turnaround_times else 0.0

        return {
            "total_approvals": total,
            "pending_approvals": pending,
            "approved_approvals": approved,
            "rejected_approvals": rejected,
            "expired_approvals": expired,
            "approval_rate": approval_rate,
            "avg_turnaround_seconds": avg_turnaround
        }

    def get_execution_detail_analytics(self, workspace_id: uuid.UUID, execution_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Returns telemetry breakdown for a single execution.
        """
        execution = self.db.query(WorkflowExecution).filter(
            and_(
                WorkflowExecution.id == execution_id,
                WorkflowExecution.workspace_id == workspace_id,
                WorkflowExecution.deleted_at.is_(None)
            )
        ).first()

        if not execution:
            return None

        total_duration = 0.0
        if execution.started_at and execution.completed_at:
            total_duration = max((execution.completed_at - execution.started_at).total_seconds(), 0.0)

        node_breakdown = []
        for en in execution.execution_nodes:
            dur = 0.0
            if en.started_at and en.completed_at:
                dur = max((en.completed_at - en.started_at).total_seconds(), 0.0)

            node_breakdown.append({
                "node_key": en.node_key,
                "status": en.status.value,
                "duration_seconds": round(dur, 2),
                "has_error": bool(en.error),
                "error": CredentialStore.redact_sensitive_str(en.error) if en.error else None
            })

        return {
            "execution_id": str(execution.id),
            "workflow_id": str(execution.workflow_id),
            "workflow_version": execution.workflow_version,
            "status": execution.status.value,
            "total_duration_seconds": round(total_duration, 2),
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "nodes": node_breakdown,
            "total_nodes": len(node_breakdown)
        }
