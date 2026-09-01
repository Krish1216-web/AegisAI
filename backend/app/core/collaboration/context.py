import uuid
import datetime
from typing import Set, Optional, Dict, Any
from pydantic import BaseModel, Field

class CollaborationContext(BaseModel):
    """
    Typed Phase 9 Collaboration Context.
    Carries workspace identity, team scoping, user membership, and correlation ID.
    Enforces strict tenant boundary constraints.
    """
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    team_id: Optional[uuid.UUID] = None
    membership_id: Optional[uuid.UUID] = None
    permissions: Set[str] = Field(default_factory=set)
    correlation_id: str = Field(default_factory=lambda: f"collab_corr_{uuid.uuid4().hex[:12]}")
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def assert_same_tenant(self, target_workspace_id: uuid.UUID) -> None:
        if self.workspace_id != target_workspace_id:
            raise PermissionError(
                f"Cross-tenant collaboration violation: caller workspace '{self.workspace_id}' "
                f"cannot access target workspace '{target_workspace_id}'."
            )
