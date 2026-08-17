import uuid
import json
import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
import redis
from loguru import logger
from pydantic import BaseModel, Field

from app.database.session import get_db
from app.database.redis import get_redis
from app.api.dependencies import get_current_user, get_workspace_member, check_rate_limit
from app.models.user import User
from app.services.ai_service import AIService
from app.core.agent.checkpoint import BaseCheckpointer
from app.core.agent.pipeline import AegisAIPipeline
from app.core.agent.state import ExecutionStatus
from app.core.agent.response import ResponseGenerationResult
from app.models.ai import Execution, AgentExecution, ExecutionEvent
from app.core.agent.exceptions import MemoryPermissionError, GraphExecutionError

router = APIRouter(prefix="/agent", tags=["Autonomous Agent Engine"])

# Global checkpointer dependency provider
def get_checkpointer(db: Session = Depends(get_db)) -> BaseCheckpointer:
    from app.core.config import settings
    from app.core.agent.postgres_checkpoint import PostgresCheckpointer
    from app.core.agent.checkpoint import InMemoryCheckpointer
    
    if settings.ENVIRONMENT == "prod":
        return PostgresCheckpointer(db)
    # For dev/test, default to postgres checkpointer if db is available
    return PostgresCheckpointer(db)

class ExecuteRequest(BaseModel):
    message: str
    workspace_id: str
    execution_id: Optional[str] = None

class ExecuteResponse(BaseModel):
    execution_id: str
    status: str
    response: Optional[str] = None
    confidence: float
    execution_time: float

class ConfirmRequest(BaseModel):
    confirmation_token: str

class EventResponseModel(BaseModel):
    event_type: str
    agent_type: Optional[str] = None
    status: str
    timestamp: datetime.datetime
    metadata: Optional[Dict[str, Any]] = None

class AgentExecResponseModel(BaseModel):
    agent_type: str
    status: str
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    duration: Optional[float] = None
    retry_count: int
    quality_score: Optional[float] = None
    error: Optional[str] = None

class StatusResponse(BaseModel):
    execution_id: str
    status: str
    current_agent: Optional[str] = None
    started_at: datetime.datetime
    completed_at: Optional[datetime.datetime] = None
    total_execution_time: Optional[float] = None
    critic_score: Optional[float] = None
    response_confidence: Optional[float] = None
    final_response: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None
    agent_executions: List[AgentExecResponseModel] = []
    events: List[EventResponseModel] = []

def make_error_response(code: str, message: str, status_code: int = 500) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message
            }
        }
    )

@router.post("/execute", response_model=ExecuteResponse, dependencies=[Depends(check_rate_limit)])
async def execute_agent_workflow(
    payload: ExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    checkpointer: BaseCheckpointer = Depends(get_checkpointer)
):
    """
    Triggers the multi-agent pipeline and returns the final response.
    """
    # Validate workspace membership
    try:
        ws_uuid = uuid.UUID(payload.workspace_id)
        get_workspace_member(ws_uuid, current_user, db)
    except (ValueError, HTTPException):
        return make_error_response("PERMISSION_DENIED", "User does not have access permissions for this workspace.", 403)

    execution_id = payload.execution_id or str(uuid.uuid4())
    
    # Distributed execution lock
    lock_key = f"aegis:execution:{execution_id}"
    is_locked = redis_client.set(lock_key, "locked", ex=300, nx=True)
    if not is_locked:
        return make_error_response("DUPLICATE_EXECUTION", "Execution is already in progress.", 409)
        
    try:
        ai_service = AIService(db, redis_client)
        pipeline = AegisAIPipeline(ai_service, checkpointer=checkpointer, db=db)
        
        initial_state = pipeline.build_initial_state(
            user_id=str(current_user.id),
            workspace_id=payload.workspace_id,
            execution_id=execution_id,
            original_prompt=payload.message
        )
        
        final_state = await pipeline.execute(initial_state)
        
        # Extract response and confidence
        resp_agent = final_state["agent_outputs"].get("ResponseGeneratorAgent")
        content = ""
        confidence = 0.0
        if resp_agent:
            try:
                res_obj = ResponseGenerationResult.model_validate_json(resp_agent["output"])
                content = res_obj.content
                confidence = res_obj.confidence
            except Exception:
                pass
                
        return ExecuteResponse(
            execution_id=execution_id,
            status=final_state["execution_status"].value if hasattr(final_state["execution_status"], "value") else final_state["execution_status"],
            response=content or final_state.get("final_response"),
            confidence=confidence or final_state.get("confidence_score", 0.0),
            execution_time=final_state.get("execution_time", 0.0)
        )
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        return make_error_response("EXECUTION_FAILED", "The execution could not be completed.", 500)
    finally:
        redis_client.delete(lock_key)

@router.post("/execute/stream", dependencies=[Depends(check_rate_limit)])
async def execute_agent_stream(
    payload: ExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    checkpointer: BaseCheckpointer = Depends(get_checkpointer)
):
    """
    Streams multi-agent node completion events via SSE (Server-Sent Events).
    """
    try:
        ws_uuid = uuid.UUID(payload.workspace_id)
        get_workspace_member(ws_uuid, current_user, db)
    except (ValueError, HTTPException):
        return make_error_response("PERMISSION_DENIED", "User does not have access permissions for this workspace.", 403)

    execution_id = payload.execution_id or str(uuid.uuid4())
    lock_key = f"aegis:execution:{execution_id}"
    is_locked = redis_client.set(lock_key, "locked", ex=300, nx=True)
    if not is_locked:
        return make_error_response("DUPLICATE_EXECUTION", "Execution is already in progress.", 409)

    async def sse_event_generator():
        try:
            ai_service = AIService(db, redis_client)
            pipeline = AegisAIPipeline(ai_service, checkpointer=checkpointer, db=db)
            initial_state = pipeline.build_initial_state(
                user_id=str(current_user.id),
                workspace_id=payload.workspace_id,
                execution_id=execution_id,
                original_prompt=payload.message
            )
            async for event in pipeline.stream(initial_state):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'ExecutionFailed', 'execution_id': execution_id, 'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'failed', 'error': str(e)})}\n\n"
        finally:
            redis_client.delete(lock_key)
            
    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")

@router.get("/executions", response_model=List[StatusResponse])
async def get_execution_history(
    limit: int = 10,
    offset: int = 0,
    status: Optional[str] = None,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the execution history for the authenticated user with optional filtering.
    """
    query = db.query(Execution).filter(Execution.user_id == current_user.id)
    
    if status:
        query = query.filter(Execution.status == status)
    if start_date:
        query = query.filter(Execution.started_at >= start_date)
    if end_date:
        query = query.filter(Execution.started_at <= end_date)
        
    executions = query.order_by(Execution.created_at.desc()).offset(offset).limit(limit).all()
    
    response = []
    for exec_row in executions:
        agent_execs = [
            AgentExecResponseModel(
                agent_type=ae.agent_type,
                status=ae.status,
                started_at=ae.started_at,
                completed_at=ae.completed_at,
                duration=ae.duration,
                retry_count=ae.retry_count,
                quality_score=ae.quality_score,
                error=ae.error
            )
            for ae in exec_row.agent_executions
        ]
        events = [
            EventResponseModel(
                event_type=ev.event_type,
                agent_type=ev.agent_type,
                status=ev.status,
                timestamp=ev.timestamp,
                metadata=ev.meta_data
            )
            for ev in exec_row.events
        ]
        response.append(
            StatusResponse(
                execution_id=str(exec_row.id),
                status=exec_row.status,
                current_agent=exec_row.current_agent,
                started_at=exec_row.started_at,
                completed_at=exec_row.completed_at,
                total_execution_time=exec_row.total_execution_time,
                critic_score=exec_row.critic_score,
                response_confidence=exec_row.response_confidence,
                final_response=exec_row.final_response,
                meta_data=exec_row.meta_data,
                agent_executions=agent_execs,
                events=events
            )
        )
    return response

@router.get("/executions/{execution_id}", response_model=StatusResponse)
async def get_execution_details(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves execution details from PostgreSQL, validating user ownership.
    """
    try:
        exec_uuid = uuid.UUID(execution_id)
    except ValueError:
        return make_error_response("INVALID_REQUEST", "Invalid execution_id format.", 400)
        
    exec_row = db.query(Execution).filter(Execution.id == exec_uuid).first()
    if not exec_row:
        return make_error_response("NOT_FOUND", "Execution checkpoint not found.", 404)
        
    if exec_row.user_id != current_user.id:
        return make_error_response("PERMISSION_DENIED", "Forbidden: isolation violation.", 403)
        
    agent_execs = [
        AgentExecResponseModel(
            agent_type=ae.agent_type,
            status=ae.status,
            started_at=ae.started_at,
            completed_at=ae.completed_at,
            duration=ae.duration,
            retry_count=ae.retry_count,
            quality_score=ae.quality_score,
            error=ae.error
        )
        for ae in exec_row.agent_executions
    ]
    events = [
        EventResponseModel(
            event_type=ev.event_type,
            agent_type=ev.agent_type,
            status=ev.status,
            timestamp=ev.timestamp,
            metadata=ev.meta_data
        )
        for ev in exec_row.events
    ]
    
    return StatusResponse(
        execution_id=str(exec_row.id),
        status=exec_row.status,
        current_agent=exec_row.current_agent,
        started_at=exec_row.started_at,
        completed_at=exec_row.completed_at,
        total_execution_time=exec_row.total_execution_time,
        critic_score=exec_row.critic_score,
        response_confidence=exec_row.response_confidence,
        final_response=exec_row.final_response,
        meta_data=exec_row.meta_data,
        agent_executions=agent_execs,
        events=events
    )

@router.post("/executions/{execution_id}/resume", response_model=ExecuteResponse)
async def resume_execution(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    checkpointer: BaseCheckpointer = Depends(get_checkpointer)
):
    """
    Resumes a paused execution from its persistent checkpoint.
    """
    # Distributed execution lock
    lock_key = f"aegis:execution:{execution_id}"
    is_locked = redis_client.set(lock_key, "locked", ex=300, nx=True)
    if not is_locked:
        return make_error_response("DUPLICATE_EXECUTION", "Execution is already in progress.", 409)

    try:
        ai_service = AIService(db, redis_client)
        pipeline = AegisAIPipeline(ai_service, checkpointer=checkpointer, db=db)
        
        # Load and verify checkpoint
        try:
            state = checkpointer.load(execution_id, user_id=str(current_user.id))
        except MemoryPermissionError:
            return make_error_response("PERMISSION_DENIED", "Forbidden: isolation violation.", 403)
            
        if not state:
            return make_error_response("NOT_FOUND", "Execution checkpoint not found.", 404)
            
        # Verify workspace membership
        try:
            get_workspace_member(uuid.UUID(state["workspace_id"]), current_user, db)
        except Exception:
            return make_error_response("PERMISSION_DENIED", "User does not have access permissions for this workspace.", 403)
            
        final_state = await pipeline.resume_execution(execution_id, user_id=str(current_user.id), workspace_id=state["workspace_id"])
        
        # Extract response generator output
        resp_agent = final_state["agent_outputs"].get("ResponseGeneratorAgent")
        content = ""
        confidence = 0.0
        if resp_agent:
            try:
                res_obj = ResponseGenerationResult.model_validate_json(resp_agent["output"])
                content = res_obj.content
                confidence = res_obj.confidence
            except Exception:
                pass
                
        return ExecuteResponse(
            execution_id=execution_id,
            status=final_state["execution_status"].value if hasattr(final_state["execution_status"], "value") else final_state["execution_status"],
            response=content or final_state.get("final_response"),
            confidence=confidence or final_state.get("confidence_score", 0.0),
            execution_time=final_state.get("execution_time", 0.0)
        )
    except MemoryPermissionError:
        return make_error_response("PERMISSION_DENIED", "Forbidden: isolation violation.", 403)
    except Exception as e:
        logger.error(f"Resume failed: {e}")
        return make_error_response("EXECUTION_FAILED", "The execution could not be resumed.", 500)
    finally:
        redis_client.delete(lock_key)

@router.post("/executions/{execution_id}/confirm", response_model=ExecuteResponse)
async def confirm_execution(
    execution_id: str,
    payload: ConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    checkpointer: BaseCheckpointer = Depends(get_checkpointer)
):
    """
    Confirms and resumes a pending tool execution.
    """
    lock_key = f"aegis:execution:{execution_id}"
    is_locked = redis_client.set(lock_key, "locked", ex=300, nx=True)
    if not is_locked:
        return make_error_response("DUPLICATE_EXECUTION", "Execution is already in progress.", 409)

    try:
        ai_service = AIService(db, redis_client)
        pipeline = AegisAIPipeline(ai_service, checkpointer=checkpointer, db=db)
        
        # Load and verify checkpoint
        try:
            state = checkpointer.load(execution_id, user_id=str(current_user.id))
        except MemoryPermissionError:
            return make_error_response("PERMISSION_DENIED", "Forbidden: isolation violation.", 403)
            
        if not state:
            return make_error_response("NOT_FOUND", "Execution checkpoint not found.", 404)
            
        # Verify workspace membership
        try:
            get_workspace_member(uuid.UUID(state["workspace_id"]), current_user, db)
        except Exception:
            return make_error_response("PERMISSION_DENIED", "User does not have access permissions for this workspace.", 403)
            
        # Prevent replay attacks
        from app.models.ai import ToolExecution
        completed_tool = db.query(ToolExecution).filter(
            ToolExecution.execution_id == uuid.UUID(execution_id),
            ToolExecution.status == "COMPLETED"
        ).first()
        if completed_tool:
            return make_error_response("CONFIRMATION_REPLAY", "Tool execution already completed. Replay prevented.", 400)
            
        final_state = await pipeline.resume_after_confirmation(
            execution_id,
            user_id=str(current_user.id),
            workspace_id=state["workspace_id"],
            confirmation_token=payload.confirmation_token
        )
        
        resp_agent = final_state["agent_outputs"].get("ResponseGeneratorAgent")
        content = ""
        confidence = 0.0
        if resp_agent:
            try:
                res_obj = ResponseGenerationResult.model_validate_json(resp_agent["output"])
                content = res_obj.content
                confidence = res_obj.confidence
            except Exception:
                pass
                
        return ExecuteResponse(
            execution_id=execution_id,
            status=final_state["execution_status"].value if hasattr(final_state["execution_status"], "value") else final_state["execution_status"],
            response=content or final_state.get("final_response"),
            confidence=confidence or final_state.get("confidence_score", 0.0),
            execution_time=final_state.get("execution_time", 0.0)
        )
    except MemoryPermissionError:
        return make_error_response("PERMISSION_DENIED", "Forbidden: isolation violation.", 403)
    except Exception as e:
        logger.error(f"Confirmation resume failed: {e}")
        return make_error_response("EXECUTION_FAILED", "The execution confirmation could not be completed.", 500)
    finally:
        redis_client.delete(lock_key)

@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    checkpointer: BaseCheckpointer = Depends(get_checkpointer)
):
    """
    Cancels an active agent execution, broadcasting a cancellation signal through Redis.
    """
    try:
        ai_service = AIService(db, redis_client)
        pipeline = AegisAIPipeline(ai_service, checkpointer=checkpointer, db=db)
        
        # Load and verify
        try:
            state = checkpointer.load(execution_id, user_id=str(current_user.id))
        except MemoryPermissionError:
            return make_error_response("PERMISSION_DENIED", "Forbidden: isolation violation.", 403)
            
        if not state:
            return make_error_response("NOT_FOUND", "Execution checkpoint not found.", 404)
            
        # Set cancel flag in Redis with expiration
        cancel_key = f"aegis:cancel:{execution_id}"
        redis_client.set(cancel_key, "true", ex=300)
        
        await pipeline.cancel(execution_id, user_id=str(current_user.id), workspace_id=state["workspace_id"])
        
        return {"success": True, "message": "Cancellation request registered."}
    except MemoryPermissionError:
        return make_error_response("PERMISSION_DENIED", "Forbidden: isolation violation.", 403)
    except Exception as e:
        logger.error(f"Cancellation failed: {e}")
        return make_error_response("EXECUTION_FAILED", "The execution cancellation could not be processed.", 500)
