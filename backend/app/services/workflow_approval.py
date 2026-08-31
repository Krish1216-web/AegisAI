import uuid
import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from loguru import logger

from app.models.workflow import (
    Workflow,
    WorkflowNode,
    WorkflowExecution,
    WorkflowExecutionNode,
    WorkflowExecutionStatus,
    WorkflowNodeStatus,
    WorkflowApprovalRequest,
    WorkflowApprovalStatus,
    WorkflowApprovalPolicy
)
from app.models.user import User, Role
from app.models.workspace import WorkspaceMember
from app.core.mcp.security import CredentialStore

MAX_REASON_LENGTH = 1000
MAX_MESSAGE_LENGTH = 2000

class WorkflowApprovalService:
    """
    Production-grade, tenant-isolated Human Approval & Governance service.
    Handles approval request creation, RBAC authorization, multi-approver policies,
    requester/approver separation, timeouts, cancellation, and immutable audit logs.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_approval_request(
        self,
        execution: WorkflowExecution,
        node_def: Dict[str, Any],
        requested_by_id: uuid.UUID
    ) -> WorkflowApprovalRequest:
        """
        Creates and persists a new pending WorkflowApprovalRequest.
        """
        config = node_def.get("config", {})
        node_key = node_def.get("node_key", "unknown")
        node_id_val = node_def.get("id")
        workflow_node_id = uuid.UUID(str(node_id_val)) if node_id_val else None

        title = str(config.get("title") or f"Approval Request for {node_key}")[:200]
        msg = str(config.get("approval_message") or config.get("prompt") or f"Approval required for node '{node_key}'")[:MAX_MESSAGE_LENGTH]
        timeout_seconds = int(config.get("timeout_seconds") or config.get("timeout") or 86400)
        if timeout_seconds <= 0:
            timeout_seconds = 86400

        now = datetime.datetime.now(datetime.timezone.utc)
        expires_at = now + datetime.timedelta(seconds=timeout_seconds)

        assigned_roles = config.get("approver_roles") or ["admin"]
        if not isinstance(assigned_roles, list):
            assigned_roles = [str(assigned_roles)]

        assigned_users = config.get("approver_users") or []
        if not isinstance(assigned_users, list):
            assigned_users = [str(assigned_users)]

        policy_str = str(config.get("policy", "single_approver")).lower()
        try:
            policy = WorkflowApprovalPolicy(policy_str)
        except ValueError:
            policy = WorkflowApprovalPolicy.SINGLE_APPROVER

        required_count = int(config.get("required_count") or 1)
        if required_count <= 0:
            required_count = 1

        requester_can_approve = bool(config.get("requester_can_approve", False))

        approval_req = WorkflowApprovalRequest(
            id=uuid.uuid4(),
            execution_id=execution.id,
            workflow_id=execution.workflow_id,
            workflow_node_id=workflow_node_id,
            workspace_id=execution.workspace_id,
            node_key=node_key,
            requested_by=requested_by_id,
            assigned_roles=assigned_roles,
            assigned_users=assigned_users,
            status=WorkflowApprovalStatus.PENDING,
            policy=policy,
            required_count=required_count,
            requester_can_approve=requester_can_approve,
            title=title,
            message=msg,
            timeout_seconds=timeout_seconds,
            expires_at=expires_at,
            decision_history=[],
            metadata_payload={"node_config": CredentialStore.redact_sensitive_dict(config)}
        )

        self.db.add(approval_req)
        self.db.commit()
        self.db.refresh(approval_req)
        logger.info(f"Created WorkflowApprovalRequest {approval_req.id} for execution={execution.id}, node={node_key}")
        return approval_req

    def check_and_apply_expiration(self, approval: WorkflowApprovalRequest) -> bool:
        """
        Checks if an approval has expired and transitions state accordingly.
        """
        if approval.status == WorkflowApprovalStatus.PENDING and approval.expires_at:
            now = datetime.datetime.now(datetime.timezone.utc)
            # Ensure expires_at is timezone-aware
            exp = approval.expires_at if approval.expires_at.tzinfo else approval.expires_at.replace(tzinfo=datetime.timezone.utc)
            if now > exp:
                approval.status = WorkflowApprovalStatus.EXPIRED
                approval.decision = "expired"
                approval.reason = "Approval request timed out before decision was recorded."
                approval.decided_at = now
                self.db.commit()
                self.db.refresh(approval)
                logger.warning(f"WorkflowApprovalRequest {approval.id} has EXPIRED.")
                return True
        return False

    def get_approval(
        self,
        approval_id: uuid.UUID,
        workspace_id: uuid.UUID
    ) -> Optional[WorkflowApprovalRequest]:
        """
        Retrieves an approval request under strict tenant boundary.
        """
        approval = self.db.query(WorkflowApprovalRequest).filter(
            and_(
                WorkflowApprovalRequest.id == approval_id,
                WorkflowApprovalRequest.workspace_id == workspace_id,
                WorkflowApprovalRequest.deleted_at.is_(None)
            )
        ).first()

        if approval:
            self.check_and_apply_expiration(approval)

        return approval

    def list_approvals(
        self,
        workspace_id: uuid.UUID,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[WorkflowApprovalRequest], int]:
        """
        Lists approval requests in a workspace with pagination and status filter.
        """
        query = self.db.query(WorkflowApprovalRequest).filter(
            and_(
                WorkflowApprovalRequest.workspace_id == workspace_id,
                WorkflowApprovalRequest.deleted_at.is_(None)
            )
        )

        if status:
            try:
                st_enum = WorkflowApprovalStatus(status.lower())
                query = query.filter(WorkflowApprovalRequest.status == st_enum)
            except ValueError:
                pass

        total = query.count()
        results = query.order_by(desc(WorkflowApprovalRequest.created_at)).offset(offset).limit(limit).all()

        for app in results:
            self.check_and_apply_expiration(app)

        return results, total

    def _validate_approver_authorization(
        self,
        approval: WorkflowApprovalRequest,
        acting_user: User
    ) -> None:
        """
        Enforces tenant membership, role permissions, and self-approval separation rules.
        """
        # 1. Verify workspace membership
        membership = self.db.query(WorkspaceMember).filter(
            and_(
                WorkspaceMember.workspace_id == approval.workspace_id,
                WorkspaceMember.user_id == acting_user.id
            )
        ).first()

        # Check if user has global or workspace role
        user_role_name = None
        if acting_user.role_id:
            role_obj = self.db.query(Role).filter(Role.id == acting_user.role_id).first()
            if role_obj:
                user_role_name = role_obj.name.lower()

        member_role = membership.role.lower() if membership and membership.role else None
        roles_held = {r for r in [user_role_name, member_role] if r}

        is_admin = "admin" in roles_held or "owner" in roles_held or "superadmin" in roles_held

        if not membership and not is_admin:
            raise PermissionError("User is not a member of the workspace for this approval request.")

        # 2. Requester vs Approver separation
        if not approval.requester_can_approve:
            if acting_user.id == approval.requested_by:
                raise PermissionError("Self-approval is prohibited for this request (requester_can_approve=False).")

        # 3. Assigned roles / users check
        assigned_roles = [r.lower() for r in approval.assigned_roles] if approval.assigned_roles else []
        assigned_users = [str(u).lower() for u in approval.assigned_users] if approval.assigned_users else []

        role_match = any(r in assigned_roles for r in roles_held) if assigned_roles else True
        user_match = (str(acting_user.id).lower() in assigned_users) or (acting_user.username.lower() in assigned_users) if assigned_users else True

        if not is_admin:
            if assigned_roles and assigned_users:
                if not (role_match or user_match):
                    raise PermissionError(f"User is not in the assigned approver roles ({approval.assigned_roles}) or users ({approval.assigned_users}).")
            elif assigned_roles and not role_match:
                raise PermissionError(f"User role is not authorized. Required roles: {approval.assigned_roles}.")
            elif assigned_users and not user_match:
                raise PermissionError(f"User is not in the assigned approver users list.")

    def approve(
        self,
        approval_id: uuid.UUID,
        workspace_id: uuid.UUID,
        acting_user: User,
        reason: Optional[str] = None
    ) -> WorkflowApprovalRequest:
        """
        Approves an approval request and resumes the associated workflow execution.
        """
        approval = self.get_approval(approval_id, workspace_id)
        if not approval:
            raise ValueError(f"Approval request {approval_id} not found.")

        if approval.status != WorkflowApprovalStatus.PENDING:
            raise ValueError(f"Approval request is '{approval.status}', cannot approve.")

        self._validate_approver_authorization(approval, acting_user)

        now = datetime.datetime.now(datetime.timezone.utc)
        sanitized_reason = str(reason)[:MAX_REASON_LENGTH] if reason else "Approved"

        # Check duplicate decision from same user
        history = list(approval.decision_history or [])
        if any(h.get("user_id") == str(acting_user.id) for h in history):
            raise ValueError("User has already submitted an approval decision for this request.")

        history.append({
            "user_id": str(acting_user.id),
            "username": acting_user.username,
            "decision": "approved",
            "reason": sanitized_reason,
            "timestamp": now.isoformat()
        })
        approval.decision_history = history

        # Multi-approver check
        approved_count = sum(1 for h in history if h.get("decision") == "approved")

        if approval.policy == WorkflowApprovalPolicy.ALL_APPROVERS:
            required = max(len(approval.assigned_users) if approval.assigned_users else approval.required_count, 1)
        else:
            required = approval.required_count

        if approved_count >= required:
            approval.status = WorkflowApprovalStatus.APPROVED
            approval.decision = "approved"
            approval.reason = sanitized_reason
            approval.decided_by = acting_user.id
            approval.decided_at = now

            # Resume workflow execution
            from app.services.workflow_execution import WorkflowExecutionService
            exec_svc = WorkflowExecutionService(self.db)
            exec_svc.approve_execution(
                user_id=approval.requested_by,
                workspace_id=approval.workspace_id,
                execution_id=approval.execution_id,
                approved=True
            )
            logger.info(f"WorkflowApprovalRequest {approval_id} fully APPROVED by {acting_user.id}. Execution resumed.")
        else:
            logger.info(f"WorkflowApprovalRequest {approval_id} recorded partial approval ({approved_count}/{required}).")

        self.db.commit()
        self.db.refresh(approval)
        return approval

    def reject(
        self,
        approval_id: uuid.UUID,
        workspace_id: uuid.UUID,
        acting_user: User,
        reason: Optional[str] = None
    ) -> WorkflowApprovalRequest:
        """
        Rejects an approval request and terminates the associated workflow execution.
        """
        approval = self.get_approval(approval_id, workspace_id)
        if not approval:
            raise ValueError(f"Approval request {approval_id} not found.")

        if approval.status != WorkflowApprovalStatus.PENDING:
            raise ValueError(f"Approval request is '{approval.status}', cannot reject.")

        self._validate_approver_authorization(approval, acting_user)

        now = datetime.datetime.now(datetime.timezone.utc)
        sanitized_reason = str(reason)[:MAX_REASON_LENGTH] if reason else "Rejected by approver."

        history = list(approval.decision_history or [])
        history.append({
            "user_id": str(acting_user.id),
            "username": acting_user.username,
            "decision": "rejected",
            "reason": sanitized_reason,
            "timestamp": now.isoformat()
        })
        approval.decision_history = history
        approval.status = WorkflowApprovalStatus.REJECTED
        approval.decision = "rejected"
        approval.reason = sanitized_reason
        approval.decided_by = acting_user.id
        approval.decided_at = now

        # Fail / Terminate workflow execution
        from app.services.workflow_execution import WorkflowExecutionService
        exec_svc = WorkflowExecutionService(self.db)
        exec_svc.approve_execution(
            user_id=approval.requested_by,
            workspace_id=approval.workspace_id,
            execution_id=approval.execution_id,
            approved=False
        )

        self.db.commit()
        self.db.refresh(approval)
        logger.info(f"WorkflowApprovalRequest {approval_id} REJECTED by {acting_user.id}. Execution terminated.")
        return approval

    def cancel_by_execution(
        self,
        execution_id: uuid.UUID,
        workspace_id: uuid.UUID
    ) -> int:
        """
        Cancels all pending approvals for a cancelled execution.
        """
        approvals = self.db.query(WorkflowApprovalRequest).filter(
            and_(
                WorkflowApprovalRequest.execution_id == execution_id,
                WorkflowApprovalRequest.workspace_id == workspace_id,
                WorkflowApprovalRequest.status == WorkflowApprovalStatus.PENDING
            )
        ).all()

        now = datetime.datetime.now(datetime.timezone.utc)
        count = 0
        for app in approvals:
            app.status = WorkflowApprovalStatus.CANCELLED
            app.decision = "cancelled"
            app.reason = "Workflow execution was cancelled."
            app.decided_at = now
            count += 1

        if count > 0:
            self.db.commit()
        return count
