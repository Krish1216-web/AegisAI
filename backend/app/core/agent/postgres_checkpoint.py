import uuid
import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.core.agent.checkpoint import BaseCheckpointer
from app.models.ai import ExecutionCheckpoint
from app.core.agent.exceptions import MemoryPermissionError

class PostgresCheckpointer(BaseCheckpointer):
    """
    Durable PostgreSQL-backed state checkpointer for agent graph execution.
    """
    def __init__(self, db: Session):
        self.db = db

    def save(self, execution_id: str, state: Any) -> None:
        try:
            exec_uuid = uuid.UUID(execution_id) if isinstance(execution_id, str) else execution_id
        except ValueError:
            raise ValueError(f"Invalid execution_id format: {execution_id}")
            
        user_id_str = state.get("user_id")
        workspace_id_str = state.get("workspace_id")
        
        if not user_id_str or not workspace_id_str:
            raise ValueError("user_id and workspace_id are required in AgentState to save checkpoint")
            
        try:
            user_uuid = uuid.UUID(str(user_id_str)) if isinstance(user_id_str, (str, uuid.UUID)) else user_id_str
            workspace_uuid = uuid.UUID(str(workspace_id_str)) if isinstance(workspace_id_str, (str, uuid.UUID)) else workspace_id_str
        except ValueError:
            raise ValueError("Invalid user_id or workspace_id format in state")
            
        node_name = state.get("current_agent") or "unknown"
        
        # Deep copy state and make sure it is JSON serializable
        snapshot = dict(state)
        if "execution_status" in snapshot and hasattr(snapshot["execution_status"], "value"):
            snapshot["execution_status"] = snapshot["execution_status"].value
            
        checkpoint = self.db.query(ExecutionCheckpoint).filter(
            ExecutionCheckpoint.execution_id == exec_uuid
        ).first()
        
        if checkpoint:
            checkpoint.node_name = node_name
            checkpoint.state_snapshot = snapshot
        else:
            checkpoint = ExecutionCheckpoint(
                execution_id=exec_uuid,
                user_id=user_uuid,
                workspace_id=workspace_uuid,
                node_name=node_name,
                state_snapshot=snapshot
            )
            self.db.add(checkpoint)
            
        self.db.commit()

    def load(self, execution_id: str, user_id: Optional[str] = None, workspace_id: Optional[str] = None) -> Optional[Any]:
        try:
            exec_uuid = uuid.UUID(execution_id) if isinstance(execution_id, str) else execution_id
        except ValueError:
            return None
            
        checkpoint = self.db.query(ExecutionCheckpoint).filter(
            ExecutionCheckpoint.execution_id == exec_uuid
        ).first()
        
        if not checkpoint:
            return None
            
        # Strict ownership verification
        if user_id:
            try:
                user_uuid = uuid.UUID(str(user_id)) if isinstance(user_id, (str, uuid.UUID)) else user_id
                if checkpoint.user_id != user_uuid:
                    raise MemoryPermissionError("Permission denied: Checkpoint belongs to another user")
            except ValueError:
                raise MemoryPermissionError("Invalid user_id provided for checkpointer load verification")
                
        if workspace_id:
            try:
                workspace_uuid = uuid.UUID(str(workspace_id)) if isinstance(workspace_id, (str, uuid.UUID)) else workspace_id
                if checkpoint.workspace_id != workspace_uuid:
                    raise MemoryPermissionError("Permission denied: Checkpoint belongs to another workspace")
            except ValueError:
                raise MemoryPermissionError("Invalid workspace_id provided for checkpointer load verification")
                
        snapshot = checkpoint.state_snapshot
        if "execution_status" in snapshot:
            from app.core.agent.state import ExecutionStatus
            try:
                snapshot["execution_status"] = ExecutionStatus(snapshot["execution_status"])
            except ValueError:
                pass
                
        return snapshot

    def delete(self, execution_id: str) -> None:
        try:
            exec_uuid = uuid.UUID(execution_id) if isinstance(execution_id, str) else execution_id
        except ValueError:
            return
        self.db.query(ExecutionCheckpoint).filter(
            ExecutionCheckpoint.execution_id == exec_uuid
        ).delete()
        self.db.commit()

    def exists(self, execution_id: str) -> bool:
        try:
            exec_uuid = uuid.UUID(execution_id) if isinstance(execution_id, str) else execution_id
        except ValueError:
            return False
        return self.db.query(ExecutionCheckpoint).filter(
            ExecutionCheckpoint.execution_id == exec_uuid
        ).first() is not None
