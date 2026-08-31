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
    WorkflowApproveRequest
)
from app.services.workflow import (
    WorkflowService,
    VersionConflictError,
    WorkflowArchivedError
)
from app.services.workflow_execution import WorkflowExecutionService

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
