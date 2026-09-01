import uuid
import enum
from typing import Set, Optional, Dict, Any, List
from pydantic import BaseModel, Field

class TrustLevel(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNTRUSTED = "untrusted"

class SecurityContext(BaseModel):
    """
    Typed Security Context for Phase 8 platform execution.
    Carries verified tenant, user identity, permissions, and security boundaries.
    """
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    user_role: str = "viewer"
    permissions: Set[str] = Field(default_factory=set)
    trust_level: TrustLevel = TrustLevel.MEDIUM
    requires_confirmation: bool = False
    tenant_boundary_enforced: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def has_permission(self, permission: str) -> bool:
        """Check if caller has explicit permission or admin role."""
        if self.user_role == "admin":
            return True
        return permission in self.permissions

    def has_all_permissions(self, required_permissions: List[str]) -> bool:
        """Check if caller has all required permissions or admin role."""
        if self.user_role == "admin":
            return True
        return all(self.has_permission(p) for p in required_permissions)

    def assert_same_tenant(self, target_workspace_id: uuid.UUID) -> None:
        """Enforces that an operation does not cross tenant boundaries."""
        if not self.tenant_boundary_enforced:
            return
        if self.workspace_id != target_workspace_id:
            raise PermissionError(
                f"Cross-tenant access violation: Caller workspace '{self.workspace_id}' "
                f"cannot access target workspace '{target_workspace_id}'."
            )
