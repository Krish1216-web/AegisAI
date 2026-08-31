import uuid
import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.models.workflow import (
    WorkflowStatus,
    WorkflowExecutionStatus,
    WorkflowNodeStatus,
    WorkflowNodeType
)

# ---------------------------------------------------------
# Node Configuration Schemas
# ---------------------------------------------------------

class BaseNodeConfig(BaseModel):
    class Config:
        extra = "allow"

class StartNodeConfig(BaseNodeConfig):
    input_schema: Optional[Dict[str, Any]] = Field(default_factory=dict)

class EndNodeConfig(BaseNodeConfig):
    output_schema: Optional[Dict[str, Any]] = Field(default_factory=dict)
    output_template: Optional[str] = None

class AgentNodeConfig(BaseNodeConfig):
    agent_type: str = "orchestrator"
    prompt: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = 0.7

class RAGNodeConfig(BaseNodeConfig):
    query: Optional[str] = None
    top_k: int = 5
    similarity_threshold: float = 0.5
    collection_name: Optional[str] = None

class GraphNodeConfig(BaseNodeConfig):
    query: Optional[str] = None
    max_hops: int = 2
    relationship_types: Optional[List[str]] = None

class MemoryNodeConfig(BaseNodeConfig):
    action: str = "retrieve"  # retrieve, store, delete
    query: Optional[str] = None
    key: Optional[str] = None

class MCPToolNodeConfig(BaseNodeConfig):
    tool_id: Optional[str] = None
    server_id: Optional[str] = None
    tool_name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = Field(default_factory=dict)

class MCPResourceNodeConfig(BaseNodeConfig):
    resource_id: Optional[str] = None
    server_id: Optional[str] = None
    uri: Optional[str] = None

class MCPPromptNodeConfig(BaseNodeConfig):
    prompt_id: Optional[str] = None
    server_id: Optional[str] = None
    prompt_name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = Field(default_factory=dict)

class LocalToolNodeConfig(BaseNodeConfig):
    tool_name: str
    arguments: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ConditionNodeConfig(BaseNodeConfig):
    expression: Optional[str] = None
    left: Optional[str] = None
    operator: Optional[str] = "equals"
    right: Optional[Any] = None
    true_target: Optional[str] = None
    false_target: Optional[str] = None

class HumanApprovalNodeConfig(BaseNodeConfig):
    title: Optional[str] = "Approval Request"
    prompt: Optional[str] = "Please review and approve this step."
    approval_message: Optional[str] = None
    timeout_seconds: int = 86400
    timeout: Optional[int] = 86400
    approver_roles: Optional[List[str]] = Field(default_factory=lambda: ["admin"])
    approver_users: Optional[List[str]] = Field(default_factory=list)
    policy: Optional[str] = "single_approver"
    required_count: Optional[int] = 1
    requester_can_approve: Optional[bool] = False

class TransformNodeConfig(BaseNodeConfig):
    mapping: Optional[Dict[str, Any]] = Field(default_factory=dict)
    template: Optional[str] = None

class ParallelNodeConfig(BaseNodeConfig):
    max_concurrency: Optional[int] = 5
    branches: Optional[List[str]] = Field(default_factory=list)

class MergeNodeConfig(BaseNodeConfig):
    policy: str = "all"  # "all", "any", "quorum"
    quorum_count: Optional[int] = 2
    merge_key: Optional[str] = "branches"

class SubWorkflowNodeConfig(BaseNodeConfig):
    workflow_id: Optional[str] = None
    workflow_name: Optional[str] = None
    input_mapping: Optional[Dict[str, Any]] = Field(default_factory=dict)
    propagate_failure: bool = True
    timeout_seconds: Optional[int] = 300

# ---------------------------------------------------------
# Workflow Node Schemas
# ---------------------------------------------------------

class WorkflowNodeCreate(BaseModel):
    node_key: str
    node_type: WorkflowNodeType
    name: str
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    position: Optional[Dict[str, Any]] = Field(default_factory=lambda: {"x": 0, "y": 0})
    is_enabled: bool = True

class WorkflowNodeUpdate(BaseModel):
    node_key: Optional[str] = None
    node_type: Optional[WorkflowNodeType] = None
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    position: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None

class WorkflowNodeResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    node_key: str
    node_type: WorkflowNodeType
    name: str
    config: Dict[str, Any]
    position: Dict[str, Any]
    is_enabled: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

# ---------------------------------------------------------
# Workflow Edge Schemas
# ---------------------------------------------------------

class WorkflowEdgeCreate(BaseModel):
    source_node_key: Optional[str] = None
    target_node_key: Optional[str] = None
    source_node_id: Optional[uuid.UUID] = None
    target_node_id: Optional[uuid.UUID] = None
    condition: Optional[Dict[str, Any]] = None
    priority: int = 0

class WorkflowEdgeResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    condition: Optional[Dict[str, Any]] = None
    priority: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# ---------------------------------------------------------
# Workflow Variable Schemas
# ---------------------------------------------------------

class WorkflowVariableCreate(BaseModel):
    name: str
    value: Optional[str] = None
    value_type: str = "string"  # string, number, boolean, json
    is_secret: bool = False

class WorkflowVariableResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    name: str
    value: Optional[str] = None
    value_type: str
    is_secret: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

# ---------------------------------------------------------
# Workflow Validation Schemas
# ---------------------------------------------------------

class WorkflowValidationItem(BaseModel):
    code: str
    message: str
    node_key: Optional[str] = None
    edge_id: Optional[str] = None

class WorkflowValidationResult(BaseModel):
    valid: bool
    errors: List[WorkflowValidationItem] = Field(default_factory=list)
    warnings: List[WorkflowValidationItem] = Field(default_factory=list)

# ---------------------------------------------------------
# Workflow CRUD Schemas
# ---------------------------------------------------------

class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    nodes: Optional[List[WorkflowNodeCreate]] = Field(default_factory=list)
    edges: Optional[List[WorkflowEdgeCreate]] = Field(default_factory=list)
    variables: Optional[List[WorkflowVariableCreate]] = Field(default_factory=list)

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[WorkflowStatus] = None
    is_active: Optional[bool] = None
    nodes: Optional[List[WorkflowNodeCreate]] = None
    edges: Optional[List[WorkflowEdgeCreate]] = None
    variables: Optional[List[WorkflowVariableCreate]] = None

class WorkflowResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: Optional[str] = None
    status: WorkflowStatus
    version: int
    is_active: bool
    node_count: int = 0
    edge_count: int = 0
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

class WorkflowDetailResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: Optional[str] = None
    status: WorkflowStatus
    version: int
    is_active: bool
    nodes: List[WorkflowNodeResponse] = Field(default_factory=list)
    edges: List[WorkflowEdgeResponse] = Field(default_factory=list)
    variables: List[WorkflowVariableResponse] = Field(default_factory=list)
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

class WorkflowListResponse(BaseModel):
    workflows: List[WorkflowResponse]
    total: int
    limit: int
    offset: int

# ---------------------------------------------------------
# Workflow Execution Schemas
# ---------------------------------------------------------

class WorkflowExecutionCreate(BaseModel):
    input_data: Optional[Dict[str, Any]] = Field(default_factory=dict)

class WorkflowExecutionNodeResponse(BaseModel):
    id: uuid.UUID
    execution_id: uuid.UUID
    node_id: Optional[uuid.UUID] = None
    node_key: str
    status: WorkflowNodeStatus
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True

class WorkflowExecutionResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    workflow_version: int
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    status: WorkflowExecutionStatus
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class WorkflowExecutionDetailResponse(WorkflowExecutionResponse):
    execution_nodes: List[WorkflowExecutionNodeResponse] = Field(default_factory=list)

class WorkflowDefinitionUpdate(BaseModel):
    expected_version: int
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: List[WorkflowNodeCreate] = Field(default_factory=list)
    edges: List[WorkflowEdgeCreate] = Field(default_factory=list)
    variables: Optional[List[WorkflowVariableCreate]] = Field(default_factory=list)

class WorkflowCloneRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class WorkflowApproveRequest(BaseModel):
    approved: bool = True
    comments: Optional[str] = None
    reason: Optional[str] = None

class WorkflowApprovalDecisionRequest(BaseModel):
    decision: str = "approved"  # "approved" or "rejected"
    reason: Optional[str] = None

class WorkflowApprovalResponse(BaseModel):
    id: uuid.UUID
    execution_id: uuid.UUID
    workflow_id: uuid.UUID
    workflow_node_id: Optional[uuid.UUID] = None
    workspace_id: uuid.UUID
    node_key: str
    requested_by: uuid.UUID
    assigned_roles: List[str] = Field(default_factory=list)
    assigned_users: List[str] = Field(default_factory=list)
    status: str
    policy: str
    required_count: int
    requester_can_approve: bool
    title: str
    message: Optional[str] = None
    timeout_seconds: int
    expires_at: Optional[datetime.datetime] = None
    decided_by: Optional[uuid.UUID] = None
    decided_at: Optional[datetime.datetime] = None
    decision: Optional[str] = None
    reason: Optional[str] = None
    decision_history: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

class WorkflowApprovalListResponse(BaseModel):
    approvals: List[WorkflowApprovalResponse]
    total: int
    limit: int
    offset: int

class WorkflowScheduleCreate(BaseModel):
    workflow_id: uuid.UUID
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    schedule_type: str = "cron"  # "cron", "one_time", "delayed"
    cron_expression: Optional[str] = None
    run_at: Optional[datetime.datetime] = None
    timezone: str = "UTC"
    is_enabled: bool = True
    concurrency_policy: str = "skip"  # "skip", "allow", "queue"
    misfire_policy: str = "run_once"  # "run_once", "skip", "run_latest"
    input_data: Optional[Dict[str, Any]] = Field(default_factory=dict)

class WorkflowScheduleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    schedule_type: Optional[str] = None
    cron_expression: Optional[str] = None
    run_at: Optional[datetime.datetime] = None
    timezone: Optional[str] = None
    is_enabled: Optional[bool] = None
    concurrency_policy: Optional[str] = None
    misfire_policy: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None

class WorkflowScheduleResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    workspace_id: uuid.UUID
    created_by: uuid.UUID
    name: str
    description: Optional[str] = None
    schedule_type: str
    cron_expression: Optional[str] = None
    run_at: Optional[datetime.datetime] = None
    timezone: str
    status: str
    is_enabled: bool
    workflow_version: int
    concurrency_policy: str
    misfire_policy: str
    input_data: Dict[str, Any]
    next_run_at: Optional[datetime.datetime] = None
    last_run_at: Optional[datetime.datetime] = None
    last_execution_id: Optional[uuid.UUID] = None
    total_runs: int
    failure_count: int
    last_error: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

class WorkflowScheduleListResponse(BaseModel):
    schedules: List[WorkflowScheduleResponse]
    total: int
    limit: int
    offset: int
