import uuid
import datetime
import zoneinfo
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from loguru import logger

from app.models.workflow import (
    Workflow,
    WorkflowStatus,
    WorkflowExecution,
    WorkflowExecutionStatus,
    WorkflowSchedule,
    WorkflowScheduleType,
    WorkflowScheduleStatus,
    WorkflowScheduleConcurrencyPolicy,
    WorkflowScheduleMisfirePolicy
)
from app.models.user import User, Role
from app.models.workspace import WorkspaceMember
from app.schemas.workflow import (
    WorkflowScheduleCreate,
    WorkflowScheduleUpdate
)
from app.services.workflow_cron import CronEvaluator, CronValidationError
from app.services.workflow_execution import WorkflowExecutionService

MAX_SCHEDULES_PER_WORKSPACE = 100
MAX_SCHEDULES_PER_WORKFLOW = 20

class WorkflowSchedulerService:
    """
    Production-grade, tenant-isolated workflow scheduling service.
    Handles CRON, ONE_TIME, and DELAYED recurring schedules, version pinning,
    concurrency control, misfire policies, and execution engine integration.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_schedule(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        payload: WorkflowScheduleCreate
    ) -> WorkflowSchedule:
        """
        Creates and persists a new workflow schedule.
        """
        # 1. Workspace count limits
        ws_count = self.db.query(WorkflowSchedule).filter(
            and_(
                WorkflowSchedule.workspace_id == workspace_id,
                WorkflowSchedule.deleted_at.is_(None)
            )
        ).count()
        if ws_count >= MAX_SCHEDULES_PER_WORKSPACE:
            raise ValueError(f"Workspace schedule limit ({MAX_SCHEDULES_PER_WORKSPACE}) reached.")

        # 2. Workflow verification & ownership
        workflow = self.db.query(Workflow).filter(
            and_(
                Workflow.id == payload.workflow_id,
                Workflow.workspace_id == workspace_id,
                Workflow.deleted_at.is_(None)
            )
        ).first()
        if not workflow:
            raise ValueError(f"Workflow '{payload.workflow_id}' not found in active workspace.")

        if workflow.status == WorkflowStatus.ARCHIVED:
            raise ValueError(f"Cannot create schedule for archived workflow '{workflow.id}'.")

        wf_sched_count = self.db.query(WorkflowSchedule).filter(
            and_(
                WorkflowSchedule.workflow_id == payload.workflow_id,
                WorkflowSchedule.deleted_at.is_(None)
            )
        ).count()
        if wf_sched_count >= MAX_SCHEDULES_PER_WORKFLOW:
            raise ValueError(f"Workflow schedule limit ({MAX_SCHEDULES_PER_WORKFLOW}) reached for workflow '{workflow.id}'.")

        # 3. Timezone validation
        tz_name = (payload.timezone or "UTC").strip()
        CronEvaluator.validate_timezone(tz_name)

        # 4. Schedule type & next_run_at calculation
        sched_type_str = payload.schedule_type.lower()
        try:
            sched_type = WorkflowScheduleType(sched_type_str)
        except ValueError:
            raise ValueError(f"Invalid schedule type '{payload.schedule_type}'. Supported: cron, one_time, delayed.")

        now = datetime.datetime.now(datetime.timezone.utc)
        next_run_at: Optional[datetime.datetime] = None

        if sched_type == WorkflowScheduleType.CRON:
            if not payload.cron_expression:
                raise ValueError("Cron expression is required for 'cron' schedule type.")
            # Validate expression
            CronEvaluator.parse_cron(payload.cron_expression)
            next_run_at = CronEvaluator.get_next_run(payload.cron_expression, from_dt=now, tz_name=tz_name)

        elif sched_type in [WorkflowScheduleType.ONE_TIME, WorkflowScheduleType.DELAYED]:
            if not payload.run_at:
                raise ValueError(f"run_at timestamp is required for '{sched_type.value}' schedule type.")
            run_at_utc = payload.run_at if payload.run_at.tzinfo else payload.run_at.replace(tzinfo=datetime.timezone.utc)
            if run_at_utc <= now:
                raise ValueError(f"Scheduled run_at time must be in the future (got {run_at_utc.isoformat()}).")
            next_run_at = run_at_utc

        # 5. Policies
        try:
            concurrency_policy = WorkflowScheduleConcurrencyPolicy(payload.concurrency_policy.lower())
        except ValueError:
            concurrency_policy = WorkflowScheduleConcurrencyPolicy.SKIP

        try:
            misfire_policy = WorkflowScheduleMisfirePolicy(payload.misfire_policy.lower())
        except ValueError:
            misfire_policy = WorkflowScheduleMisfirePolicy.RUN_ONCE

        schedule = WorkflowSchedule(
            id=uuid.uuid4(),
            workflow_id=workflow.id,
            workspace_id=workspace_id,
            created_by=user_id,
            name=payload.name.strip()[:100],
            description=payload.description,
            schedule_type=sched_type,
            cron_expression=payload.cron_expression,
            run_at=payload.run_at,
            timezone=tz_name,
            status=WorkflowScheduleStatus.ACTIVE if payload.is_enabled else WorkflowScheduleStatus.PAUSED,
            is_enabled=payload.is_enabled,
            workflow_version=workflow.version,  # Pin to current workflow version
            concurrency_policy=concurrency_policy,
            misfire_policy=misfire_policy,
            input_data=payload.input_data or {},
            next_run_at=next_run_at if payload.is_enabled else None,
            total_runs=0,
            failure_count=0
        )

        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        logger.info(f"Created WorkflowSchedule {schedule.id} for workflow={workflow.id}, next_run={next_run_at}")
        return schedule

    def get_schedule(
        self,
        schedule_id: uuid.UUID,
        workspace_id: uuid.UUID
    ) -> Optional[WorkflowSchedule]:
        """Retrieves schedule under workspace boundary."""
        return self.db.query(WorkflowSchedule).filter(
            and_(
                WorkflowSchedule.id == schedule_id,
                WorkflowSchedule.workspace_id == workspace_id,
                WorkflowSchedule.deleted_at.is_(None)
            )
        ).first()

    def list_schedules(
        self,
        workspace_id: uuid.UUID,
        workflow_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[WorkflowSchedule], int]:
        """Lists schedules in workspace with pagination and filters."""
        query = self.db.query(WorkflowSchedule).filter(
            and_(
                WorkflowSchedule.workspace_id == workspace_id,
                WorkflowSchedule.deleted_at.is_(None)
            )
        )

        if workflow_id:
            query = query.filter(WorkflowSchedule.workflow_id == workflow_id)

        if status:
            try:
                st = WorkflowScheduleStatus(status.lower())
                query = query.filter(WorkflowSchedule.status == st)
            except ValueError:
                pass

        total = query.count()
        results = query.order_by(desc(WorkflowSchedule.created_at)).offset(offset).limit(limit).all()
        return results, total

    def update_schedule(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        schedule_id: uuid.UUID,
        payload: WorkflowScheduleUpdate
    ) -> WorkflowSchedule:
        """Updates schedule parameters and recomputes next_run_at if schedule fields changed."""
        schedule = self.get_schedule(schedule_id, workspace_id)
        if not schedule:
            raise ValueError(f"Schedule '{schedule_id}' not found.")

        if payload.name is not None:
            schedule.name = payload.name.strip()[:100]
        if payload.description is not None:
            schedule.description = payload.description
        if payload.input_data is not None:
            schedule.input_data = payload.input_data

        if payload.timezone is not None:
            tz_name = payload.timezone.strip()
            CronEvaluator.validate_timezone(tz_name)
            schedule.timezone = tz_name

        if payload.schedule_type is not None:
            try:
                schedule.schedule_type = WorkflowScheduleType(payload.schedule_type.lower())
            except ValueError:
                raise ValueError(f"Invalid schedule type '{payload.schedule_type}'.")

        if payload.cron_expression is not None:
            CronEvaluator.parse_cron(payload.cron_expression)
            schedule.cron_expression = payload.cron_expression

        if payload.run_at is not None:
            schedule.run_at = payload.run_at

        if payload.concurrency_policy is not None:
            try:
                schedule.concurrency_policy = WorkflowScheduleConcurrencyPolicy(payload.concurrency_policy.lower())
            except ValueError:
                pass

        if payload.misfire_policy is not None:
            try:
                schedule.misfire_policy = WorkflowScheduleMisfirePolicy(payload.misfire_policy.lower())
            except ValueError:
                pass

        if payload.is_enabled is not None:
            schedule.is_enabled = payload.is_enabled
            if payload.is_enabled:
                schedule.status = WorkflowScheduleStatus.ACTIVE
            else:
                schedule.status = WorkflowScheduleStatus.PAUSED

        # Recompute next_run_at if active
        now = datetime.datetime.now(datetime.timezone.utc)
        if schedule.is_enabled and schedule.status == WorkflowScheduleStatus.ACTIVE:
            if schedule.schedule_type == WorkflowScheduleType.CRON and schedule.cron_expression:
                schedule.next_run_at = CronEvaluator.get_next_run(schedule.cron_expression, from_dt=now, tz_name=schedule.timezone)
            elif schedule.schedule_type in [WorkflowScheduleType.ONE_TIME, WorkflowScheduleType.DELAYED] and schedule.run_at:
                run_at_utc = schedule.run_at if schedule.run_at.tzinfo else schedule.run_at.replace(tzinfo=datetime.timezone.utc)
                schedule.next_run_at = run_at_utc if run_at_utc > now else None
        else:
            schedule.next_run_at = None

        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def pause_schedule(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        schedule_id: uuid.UUID
    ) -> WorkflowSchedule:
        """Pauses schedule execution."""
        schedule = self.get_schedule(schedule_id, workspace_id)
        if not schedule:
            raise ValueError(f"Schedule '{schedule_id}' not found.")

        schedule.status = WorkflowScheduleStatus.PAUSED
        schedule.is_enabled = False
        schedule.next_run_at = None
        self.db.commit()
        self.db.refresh(schedule)
        logger.info(f"Paused WorkflowSchedule {schedule_id}")
        return schedule

    def resume_schedule(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        schedule_id: uuid.UUID
    ) -> WorkflowSchedule:
        """Resumes active schedule and recalculates next_run_at."""
        schedule = self.get_schedule(schedule_id, workspace_id)
        if not schedule:
            raise ValueError(f"Schedule '{schedule_id}' not found.")

        schedule.status = WorkflowScheduleStatus.ACTIVE
        schedule.is_enabled = True

        now = datetime.datetime.now(datetime.timezone.utc)
        if schedule.schedule_type == WorkflowScheduleType.CRON and schedule.cron_expression:
            schedule.next_run_at = CronEvaluator.get_next_run(schedule.cron_expression, from_dt=now, tz_name=schedule.timezone)
        elif schedule.schedule_type in [WorkflowScheduleType.ONE_TIME, WorkflowScheduleType.DELAYED] and schedule.run_at:
            run_at_utc = schedule.run_at if schedule.run_at.tzinfo else schedule.run_at.replace(tzinfo=datetime.timezone.utc)
            if run_at_utc > now:
                schedule.next_run_at = run_at_utc
            else:
                schedule.status = WorkflowScheduleStatus.EXPIRED
                schedule.next_run_at = None

        self.db.commit()
        self.db.refresh(schedule)
        logger.info(f"Resumed WorkflowSchedule {schedule_id}, next_run={schedule.next_run_at}")
        return schedule

    def delete_schedule(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        schedule_id: uuid.UUID
    ) -> bool:
        """Soft deletes schedule."""
        schedule = self.get_schedule(schedule_id, workspace_id)
        if not schedule:
            return False

        schedule.deleted_at = datetime.datetime.now(datetime.timezone.utc)
        schedule.is_enabled = False
        schedule.status = WorkflowScheduleStatus.DISABLED
        schedule.next_run_at = None
        self.db.commit()
        logger.info(f"Soft deleted WorkflowSchedule {schedule_id}")
        return True

    def trigger_schedule(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        schedule_id: uuid.UUID,
        is_manual: bool = False
    ) -> WorkflowExecution:
        """
        Executes a workflow triggered by schedule or manual invoke.
        Enforces concurrency policies, records provenance, and calculates next run.
        """
        schedule = self.get_schedule(schedule_id, workspace_id)
        if not schedule:
            raise ValueError(f"Schedule '{schedule_id}' not found.")

        if not is_manual and not schedule.is_enabled:
            raise ValueError(f"Schedule '{schedule_id}' is disabled/paused.")

        # Concurrency Check: Check if an execution is currently running
        if schedule.concurrency_policy == WorkflowScheduleConcurrencyPolicy.SKIP and schedule.last_execution_id:
            last_exec = self.db.query(WorkflowExecution).filter(
                WorkflowExecution.id == schedule.last_execution_id
            ).first()
            if last_exec and last_exec.status in [WorkflowExecutionStatus.RUNNING, WorkflowExecutionStatus.WAITING]:
                logger.warning(f"Skipping scheduled run for {schedule.id}: previous execution {last_exec.id} is still {last_exec.status.value}")
                # Recalculate next run without starting a new execution
                now = datetime.datetime.now(datetime.timezone.utc)
                if schedule.schedule_type == WorkflowScheduleType.CRON and schedule.cron_expression:
                    schedule.next_run_at = CronEvaluator.get_next_run(schedule.cron_expression, from_dt=now, tz_name=schedule.timezone)
                    self.db.commit()
                return last_exec

        # Build execution input data with provenance
        input_payload = dict(schedule.input_data or {})
        input_payload["_schedule_provenance"] = {
            "schedule_id": str(schedule.id),
            "schedule_name": schedule.name,
            "trigger_type": "manual" if is_manual else "schedule",
            "workflow_version": schedule.workflow_version,
            "triggered_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

        # Trigger execution via WorkflowExecutionService
        exec_service = WorkflowExecutionService(self.db)
        execution = exec_service.execute_workflow(
            user_id=schedule.created_by,
            workspace_id=schedule.workspace_id,
            workflow_id=schedule.workflow_id,
            input_data=input_payload
        )

        now = datetime.datetime.now(datetime.timezone.utc)
        schedule.last_run_at = now
        schedule.last_execution_id = execution.id
        schedule.total_runs += 1

        # Advance schedule state
        if schedule.schedule_type in [WorkflowScheduleType.ONE_TIME, WorkflowScheduleType.DELAYED]:
            schedule.status = WorkflowScheduleStatus.COMPLETED
            schedule.is_enabled = False
            schedule.next_run_at = None
        elif schedule.schedule_type == WorkflowScheduleType.CRON and schedule.cron_expression:
            schedule.next_run_at = CronEvaluator.get_next_run(schedule.cron_expression, from_dt=now, tz_name=schedule.timezone)

        self.db.commit()
        self.db.refresh(schedule)
        logger.info(f"Triggered execution {execution.id} for schedule {schedule.id}. Next run: {schedule.next_run_at}")
        return execution

    def poll_due_schedules(self, max_batch: int = 50) -> List[WorkflowExecution]:
        """
        Polls and triggers due schedules across all workspaces (worker mechanism).
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        due_schedules = self.db.query(WorkflowSchedule).filter(
            and_(
                WorkflowSchedule.status == WorkflowScheduleStatus.ACTIVE,
                WorkflowSchedule.is_enabled.is_(True),
                WorkflowSchedule.next_run_at.is_not(None),
                WorkflowSchedule.next_run_at <= now,
                WorkflowSchedule.deleted_at.is_(None)
            )
        ).limit(max_batch).all()

        executions = []
        for sched in due_schedules:
            try:
                exec_obj = self.trigger_schedule(
                    user_id=sched.created_by,
                    workspace_id=sched.workspace_id,
                    schedule_id=sched.id,
                    is_manual=False
                )
                executions.append(exec_obj)
            except Exception as e:
                logger.error(f"Failed triggering scheduled execution for {sched.id}: {str(e)}")
                sched.failure_count += 1
                sched.last_error = str(e)
                self.db.commit()

        return executions
