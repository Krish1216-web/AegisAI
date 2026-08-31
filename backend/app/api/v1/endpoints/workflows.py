import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from loguru import logger

from app.database.session import get_db
from app.api.dependencies import get_current_user, check_rate_limit
from app.models.user import User
from app.api.v1.endpoints.documents import resolve_workspace_id

from app.models.workflow import (
    WorkflowStatus,
    WorkflowExecutionStatus
)
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowDetailResponse,
    WorkflowListResponse,
    WorkflowValidationResult,
    WorkflowExecutionCreate,
    WorkflowExecutionResponse,
    WorkflowExecutionDetailResponse,
    WorkflowNodeResponse,
    WorkflowEdgeResponse,
    WorkflowVariableResponse,
    WorkflowExecutionNodeResponse,
    WorkflowDefinitionUpdate,
    WorkflowCloneRequest,
    WorkflowApproveRequest,
    WorkflowApprovalDecisionRequest,
    WorkflowApprovalResponse,
    WorkflowApprovalListResponse,
    WorkflowScheduleCreate,
    WorkflowScheduleUpdate,
    WorkflowScheduleResponse,
    WorkflowScheduleListResponse
)
from app.services.workflow import (
    WorkflowService,
    VersionConflictError,
    WorkflowArchivedError
)
from app.services.workflow_execution import WorkflowExecutionService
from app.services.workflow_approval import WorkflowApprovalService
from app.services.workflow_scheduler import WorkflowSchedulerService
from app.services.workflow_analytics import WorkflowAnalyticsService

router = APIRouter(prefix="/workflows", tags=["Workflows Engine"])

@router.post("", response_model=WorkflowDetailResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_rate_limit)])
async def create_workflow(
    payload: WorkflowCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Creates a new workflow definition with optional initial nodes, edges, and variables.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowService(db)
    workflow = service.create_workflow(current_user.id, workspace_id, payload)
    return workflow

@router.get("", response_model=WorkflowListResponse, dependencies=[Depends(check_rate_limit)])
async def list_workflows(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists all workflows in the authenticated workspace.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowService(db)
    workflows, total = service.list_workflows(current_user.id, workspace_id, limit, offset, status)

    items = [
        WorkflowResponse(
            id=w.id,
            user_id=w.user_id,
            workspace_id=w.workspace_id,
            name=w.name,
            description=w.description,
            status=w.status,
            version=w.version,
            is_active=w.is_active,
            node_count=len([n for n in w.nodes if not n.deleted_at]),
            edge_count=len([e for e in w.edges if not e.deleted_at]),
            created_at=w.created_at,
            updated_at=w.updated_at
        )
        for w in workflows
    ]

    return WorkflowListResponse(
        workflows=items,
        total=total,
        limit=limit,
        offset=offset
    )

@router.get("/{workflow_id}", response_model=WorkflowDetailResponse, dependencies=[Depends(check_rate_limit)])
async def get_workflow(
    workflow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves full details of a workflow, including nodes, edges, and variables.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowService(db)
    workflow = service.get_workflow(current_user.id, workspace_id, workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found in active workspace."
        )
    return workflow

@router.put("/{workflow_id}", response_model=WorkflowDetailResponse, dependencies=[Depends(check_rate_limit)])
async def update_workflow(
    workflow_id: uuid.UUID,
    payload: WorkflowUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates workflow metadata or structure (increments version if structural changes are made).
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowService(db)
    workflow = service.update_workflow(current_user.id, workspace_id, workflow_id, payload)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found in active workspace."
        )
    return workflow

@router.get("/{workflow_id}/definition", response_model=WorkflowDetailResponse, dependencies=[Depends(check_rate_limit)])
async def get_workflow_definition(
    workflow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the complete graph definition of a workflow for visual canvas loading.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowService(db)
    workflow = service.get_workflow_definition(current_user.id, workspace_id, workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found in active workspace."
        )
    return workflow

@router.put("/{workflow_id}/definition", response_model=WorkflowDetailResponse, dependencies=[Depends(check_rate_limit)])
async def update_workflow_definition(
    workflow_id: uuid.UUID,
    payload: WorkflowDefinitionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Atomically updates the complete visual workflow graph definition with optimistic concurrency protection.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowService(db)
    try:
        workflow = service.update_workflow_definition(current_user.id, workspace_id, workflow_id, payload)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow '{workflow_id}' not found in active workspace."
            )
        return workflow
    except VersionConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except WorkflowArchivedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{workflow_id}/clone", response_model=WorkflowDetailResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_rate_limit)])
async def clone_workflow(
    workflow_id: uuid.UUID,
    payload: Optional[WorkflowCloneRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clones an existing workflow into a new draft workflow.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowService(db)
    cloned = service.clone_workflow(
        current_user.id,
        workspace_id,
        workflow_id,
        clone_name=payload.name if payload else None
    )
    if not cloned:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found in active workspace."
        )
    return cloned

@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(check_rate_limit)])
async def delete_workflow(
    workflow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Soft deletes a workflow and cleans up active references.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowService(db)
    deleted = service.delete_workflow(current_user.id, workspace_id, workflow_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found in active workspace."
        )
    return None

@router.post("/{workflow_id}/validate", response_model=WorkflowValidationResult, dependencies=[Depends(check_rate_limit)])
async def validate_workflow(
    workflow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Runs deterministic DAG validation against the workflow structure.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowService(db)
    result = service.validate_workflow(current_user.id, workspace_id, workflow_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found in active workspace."
        )
    return result

@router.post("/{workflow_id}/activate", response_model=WorkflowDetailResponse, dependencies=[Depends(check_rate_limit)])
async def activate_workflow(
    workflow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validates and activates a workflow for production execution.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowService(db)
    workflow, validation = service.activate_workflow(current_user.id, workspace_id, workflow_id)
    if not workflow:
        if validation and not validation.valid:
            err_msgs = "; ".join([e.message for e in validation.errors])
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workflow validation failed: {err_msgs}"
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found in active workspace."
        )
    return workflow

@router.post("/{workflow_id}/pause", response_model=WorkflowDetailResponse, dependencies=[Depends(check_rate_limit)])
async def pause_workflow(
    workflow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Pauses an active workflow.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowService(db)
    workflow = service.pause_workflow(current_user.id, workspace_id, workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found in active workspace."
        )
    return workflow

@router.post("/{workflow_id}/archive", response_model=WorkflowDetailResponse, dependencies=[Depends(check_rate_limit)])
async def archive_workflow(
    workflow_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Archives a workflow.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowService(db)
    workflow = service.archive_workflow(current_user.id, workspace_id, workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found in active workspace."
        )
    return workflow

@router.post("/{workflow_id}/execute", response_model=WorkflowExecutionDetailResponse, dependencies=[Depends(check_rate_limit)])
async def execute_workflow(
    workflow_id: uuid.UUID,
    payload: WorkflowExecutionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes a workflow with the provided input parameters.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    exec_service = WorkflowExecutionService(db)
    try:
        execution = exec_service.execute_workflow(
            user_id=current_user.id,
            workspace_id=workspace_id,
            workflow_id=workflow_id,
            input_data=payload.input_data
        )
        return execution
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Execution error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workflow execution failed due to an internal error."
        )

@router.get("/{workflow_id}/executions", response_model=List[WorkflowExecutionResponse], dependencies=[Depends(check_rate_limit)])
async def list_workflow_executions(
    workflow_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists execution history for a given workflow.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    exec_service = WorkflowExecutionService(db)
    executions, _ = exec_service.list_executions(current_user.id, workspace_id, workflow_id, limit, offset)
    return executions

@router.get("/executions/{execution_id}", response_model=WorkflowExecutionDetailResponse, dependencies=[Depends(check_rate_limit)])
async def get_workflow_execution(
    execution_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves execution trace details for a specific workflow execution.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    exec_service = WorkflowExecutionService(db)
    execution = exec_service.get_execution(current_user.id, workspace_id, execution_id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow execution '{execution_id}' not found."
        )
    return execution

@router.post("/executions/{execution_id}/cancel", response_model=WorkflowExecutionResponse, dependencies=[Depends(check_rate_limit)])
async def cancel_workflow_execution(
    execution_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancels an active or queued workflow execution.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    exec_service = WorkflowExecutionService(db)
    execution = exec_service.cancel_execution(current_user.id, workspace_id, execution_id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow execution '{execution_id}' not found."
        )
    return execution

@router.post("/executions/{execution_id}/approve", response_model=WorkflowExecutionResponse, dependencies=[Depends(check_rate_limit)])
async def approve_workflow_execution(
    execution_id: uuid.UUID,
    payload: WorkflowApproveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approves or rejects a workflow execution paused in WAITING_APPROVAL status.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    exec_service = WorkflowExecutionService(db)
    try:
        execution = exec_service.approve_execution(
            current_user.id,
            workspace_id,
            execution_id,
            approved=payload.approved
        )
        return execution
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# ---------------------------------------------------------
# Approval Governance Endpoints
# ---------------------------------------------------------

@router.get("/approvals", response_model=WorkflowApprovalListResponse, dependencies=[Depends(check_rate_limit)])
async def list_workflow_approvals(
    status: Optional[str] = Query(None, description="Filter by approval status: pending, approved, rejected, expired, cancelled"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists approval requests within the active workspace.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowApprovalService(db)
    approvals, total = service.list_approvals(workspace_id, status=status, limit=limit, offset=offset)
    return WorkflowApprovalListResponse(approvals=approvals, total=total, limit=limit, offset=offset)

@router.get("/approvals/{approval_id}", response_model=WorkflowApprovalResponse, dependencies=[Depends(check_rate_limit)])
async def get_workflow_approval(
    approval_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves details for a specific workflow approval request under tenant isolation.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowApprovalService(db)
    approval = service.get_approval(approval_id, workspace_id)
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request '{approval_id}' not found."
        )
    return approval

@router.post("/approvals/{approval_id}/approve", response_model=WorkflowApprovalResponse, dependencies=[Depends(check_rate_limit)])
async def approve_workflow_approval(
    approval_id: uuid.UUID,
    payload: Optional[WorkflowApprovalDecisionRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Records an authorized human approval decision and resumes workflow execution.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowApprovalService(db)
    reason = payload.reason if payload else None
    try:
        approval = service.approve(approval_id, workspace_id, current_user, reason=reason)
        return approval
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/approvals/{approval_id}/reject", response_model=WorkflowApprovalResponse, dependencies=[Depends(check_rate_limit)])
async def reject_workflow_approval(
    approval_id: uuid.UUID,
    payload: Optional[WorkflowApprovalDecisionRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Records an authorized human rejection decision and terminates workflow execution.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowApprovalService(db)
    reason = payload.reason if payload else None
    try:
        approval = service.reject(approval_id, workspace_id, current_user, reason=reason)
        return approval
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# ---------------------------------------------------------
# Scheduling & Recurring Execution Endpoints
# ---------------------------------------------------------

@router.get("/schedules", response_model=WorkflowScheduleListResponse, dependencies=[Depends(check_rate_limit)])
async def list_workflow_schedules(
    workflow_id: Optional[uuid.UUID] = Query(None, description="Filter by workflow ID"),
    status: Optional[str] = Query(None, description="Filter by status: active, paused, completed, disabled, expired, error"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists all workflow execution schedules within the active workspace.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowSchedulerService(db)
    schedules, total = service.list_schedules(workspace_id, workflow_id=workflow_id, status=status, limit=limit, offset=offset)
    return WorkflowScheduleListResponse(schedules=schedules, total=total, limit=limit, offset=offset)

@router.post("/schedules", response_model=WorkflowScheduleResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_rate_limit)])
async def create_workflow_schedule(
    payload: WorkflowScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Creates a new recurring cron or one-time scheduled workflow trigger.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowSchedulerService(db)
    try:
        schedule = service.create_schedule(current_user.id, workspace_id, payload)
        return schedule
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/schedules/{schedule_id}", response_model=WorkflowScheduleResponse, dependencies=[Depends(check_rate_limit)])
async def get_workflow_schedule(
    schedule_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves details for a specific workflow schedule under tenant isolation.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowSchedulerService(db)
    schedule = service.get_schedule(schedule_id, workspace_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found."
        )
    return schedule

@router.put("/schedules/{schedule_id}", response_model=WorkflowScheduleResponse, dependencies=[Depends(check_rate_limit)])
async def update_workflow_schedule(
    schedule_id: uuid.UUID,
    payload: WorkflowScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates workflow schedule configuration, expression, or status.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowSchedulerService(db)
    try:
        schedule = service.update_schedule(current_user.id, workspace_id, schedule_id, payload)
        return schedule
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(check_rate_limit)])
async def delete_workflow_schedule(
    schedule_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Soft deletes a workflow schedule.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowSchedulerService(db)
    deleted = service.delete_schedule(current_user.id, workspace_id, schedule_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found."
        )
    return None

@router.post("/schedules/{schedule_id}/pause", response_model=WorkflowScheduleResponse, dependencies=[Depends(check_rate_limit)])
async def pause_workflow_schedule(
    schedule_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Pauses an active workflow schedule.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowSchedulerService(db)
    try:
        schedule = service.pause_schedule(current_user.id, workspace_id, schedule_id)
        return schedule
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/schedules/{schedule_id}/resume", response_model=WorkflowScheduleResponse, dependencies=[Depends(check_rate_limit)])
async def resume_workflow_schedule(
    schedule_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Resumes a paused workflow schedule and recalculates next_run_at.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowSchedulerService(db)
    try:
        schedule = service.resume_schedule(current_user.id, workspace_id, schedule_id)
        return schedule
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/schedules/{schedule_id}/trigger", response_model=WorkflowExecutionResponse, dependencies=[Depends(check_rate_limit)])
async def trigger_workflow_schedule_manual(
    schedule_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually triggers an immediate execution of the scheduled workflow.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowSchedulerService(db)
    try:
        execution = service.trigger_schedule(current_user.id, workspace_id, schedule_id, is_manual=True)
        return execution
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# =========================================================
# PHASE 7.8: WORKFLOW MONITORING & ANALYTICS ENDPOINTS
# =========================================================

@router.get("/analytics/overview", dependencies=[Depends(check_rate_limit)])
async def get_workflow_analytics_overview(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns workspace-isolated KPI overview metrics and time-series trends.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowAnalyticsService(db)
    return service.get_overview_metrics(workspace_id, days=days)

@router.get("/analytics/performance", dependencies=[Depends(check_rate_limit)])
async def get_workflow_analytics_performance(
    sort_by: str = Query("total_runs"),
    order: str = Query("desc"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns per-workflow execution volume, duration, success rates, and health classifications.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowAnalyticsService(db)
    return service.get_workflow_performance(workspace_id, sort_by=sort_by, order=order, limit=limit, offset=offset)

@router.get("/analytics/nodes", dependencies=[Depends(check_rate_limit)])
async def get_workflow_analytics_nodes(
    workflow_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns node execution metrics, duration percentiles, and bottleneck classifications.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowAnalyticsService(db)
    return service.get_node_performance(workspace_id, workflow_id=workflow_id, limit=limit)

@router.get("/analytics/failures", dependencies=[Depends(check_rate_limit)])
async def get_workflow_analytics_failures(
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns sanitized failure clusters with secret redaction.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowAnalyticsService(db)
    return service.get_failure_analytics(workspace_id, limit=limit)

@router.get("/analytics/composition", dependencies=[Depends(check_rate_limit)])
async def get_workflow_analytics_composition(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns telemetry for sub-workflow nested graphs, parallel branches, and merge policies.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowAnalyticsService(db)
    return service.get_composition_analytics(workspace_id)

@router.get("/analytics/schedules", dependencies=[Depends(check_rate_limit)])
async def get_workflow_analytics_schedules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns summary statistics for automated workflow schedules.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowAnalyticsService(db)
    return service.get_schedule_analytics(workspace_id)

@router.get("/analytics/approvals", dependencies=[Depends(check_rate_limit)])
async def get_workflow_analytics_approvals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns governance turnaround times and approval decision metrics.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowAnalyticsService(db)
    return service.get_approval_analytics(workspace_id)

@router.get("/executions/{execution_id}/analytics", dependencies=[Depends(check_rate_limit)])
async def get_workflow_execution_analytics(
    execution_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns detailed node-level telemetry and duration waterfall for a single execution.
    """
    workspace_id = resolve_workspace_id(current_user, db)
    service = WorkflowAnalyticsService(db)
    detail = service.get_execution_detail_analytics(workspace_id, execution_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution '{execution_id}' not found."
        )
    return detail
