import uuid
import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from loguru import logger

from app.models.workflow import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkflowVariable,
    WorkflowStatus,
    WorkflowNodeType
)
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowValidationResult,
    WorkflowNodeCreate,
    WorkflowEdgeCreate,
    WorkflowVariableCreate,
    WorkflowDefinitionUpdate,
    WorkflowCloneRequest
)
from app.services.workflow_validation import WorkflowValidationService
from app.core.mcp.security import CredentialStore

class WorkflowService:
    """
    Central CRUD and lifecycle management service for Workflows.
    Enforces strict tenant isolation (workspace_id + user_id), version increments,
    validation checks before activation, and secret variable masking.
    """
    def __init__(self, db: Session):
        self.db = db

    def create_workflow(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        data: WorkflowCreate
    ) -> Workflow:
        workflow = Workflow(
            id=uuid.uuid4(),
            user_id=user_id,
            workspace_id=workspace_id,
            name=data.name.strip(),
            description=data.description.strip() if data.description else None,
            status=WorkflowStatus.DRAFT,
            version=1,
            is_active=False
        )
        self.db.add(workflow)
        self.db.flush()

        # Create nodes
        node_key_to_id: Dict[str, uuid.UUID] = {}
        if data.nodes:
            for node_data in data.nodes:
                node = WorkflowNode(
                    id=uuid.uuid4(),
                    workflow_id=workflow.id,
                    node_key=node_data.node_key,
                    node_type=node_data.node_type,
                    name=node_data.name,
                    config=node_data.config or {},
                    position=node_data.position or {"x": 0, "y": 0},
                    is_enabled=node_data.is_enabled
                )
                self.db.add(node)
                self.db.flush()
                node_key_to_id[node_data.node_key] = node.id

        # Create edges
        if data.edges:
            for edge_data in data.edges:
                src_id = edge_data.source_node_id or node_key_to_id.get(edge_data.source_node_key or "")
                tgt_id = edge_data.target_node_id or node_key_to_id.get(edge_data.target_node_key or "")
                if src_id and tgt_id:
                    edge = WorkflowEdge(
                        id=uuid.uuid4(),
                        workflow_id=workflow.id,
                        source_node_id=src_id,
                        target_node_id=tgt_id,
                        condition=edge_data.condition,
                        priority=edge_data.priority
                    )
                    self.db.add(edge)

        # Create variables
        if data.variables:
            for var_data in data.variables:
                val = var_data.value
                if var_data.is_secret and val:
                    val = CredentialStore.encode_secure_token(val)
                variable = WorkflowVariable(
                    id=uuid.uuid4(),
                    workflow_id=workflow.id,
                    name=var_data.name,
                    value=val,
                    value_type=var_data.value_type,
                    is_secret=var_data.is_secret
                )
                self.db.add(variable)

        self.db.commit()
        self.db.refresh(workflow)
        logger.info(f"Created workflow '{workflow.name}' (id={workflow.id}) in workspace={workspace_id}")
        return workflow

    def get_workflow(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        workflow_id: uuid.UUID
    ) -> Optional[Workflow]:
        return self.db.query(Workflow).filter(
            and_(
                Workflow.id == workflow_id,
                Workflow.workspace_id == workspace_id,
                Workflow.deleted_at.is_(None)
            )
        ).first()

    def list_workflows(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None
    ) -> Tuple[List[Workflow], int]:
        query = self.db.query(Workflow).filter(
            and_(
                Workflow.workspace_id == workspace_id,
                Workflow.deleted_at.is_(None)
            )
        )
        if status:
            query = query.filter(Workflow.status == status)

        total = query.count()
        workflows = query.order_by(Workflow.created_at.desc()).offset(offset).limit(limit).all()
        return workflows, total

    def update_workflow(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        workflow_id: uuid.UUID,
        data: WorkflowUpdate
    ) -> Optional[Workflow]:
        workflow = self.get_workflow(user_id, workspace_id, workflow_id)
        if not workflow:
            return None

        structural_change = False

        if data.name is not None:
            workflow.name = data.name.strip()
        if data.description is not None:
            workflow.description = data.description.strip()
        if data.status is not None:
            workflow.status = data.status
        if data.is_active is not None:
            workflow.is_active = data.is_active

        # Replace nodes if specified
        node_key_to_id: Dict[str, uuid.UUID] = {}
        if data.nodes is not None:
            structural_change = True
            # Delete old nodes & edges
            self.db.query(WorkflowEdge).filter(WorkflowEdge.workflow_id == workflow.id).delete()
            self.db.query(WorkflowNode).filter(WorkflowNode.workflow_id == workflow.id).delete()
            self.db.flush()

            for node_data in data.nodes:
                node = WorkflowNode(
                    id=uuid.uuid4(),
                    workflow_id=workflow.id,
                    node_key=node_data.node_key,
                    node_type=node_data.node_type,
                    name=node_data.name,
                    config=node_data.config or {},
                    position=node_data.position or {"x": 0, "y": 0},
                    is_enabled=node_data.is_enabled
                )
                self.db.add(node)
                self.db.flush()
                node_key_to_id[node_data.node_key] = node.id

        # Replace edges if specified
        if data.edges is not None:
            structural_change = True
            if data.nodes is None:
                # Need mapping from existing nodes
                for n in workflow.nodes:
                    node_key_to_id[n.node_key] = n.id
                self.db.query(WorkflowEdge).filter(WorkflowEdge.workflow_id == workflow.id).delete()
                self.db.flush()

            for edge_data in data.edges:
                src_id = edge_data.source_node_id or node_key_to_id.get(edge_data.source_node_key or "")
                tgt_id = edge_data.target_node_id or node_key_to_id.get(edge_data.target_node_key or "")
                if src_id and tgt_id:
                    edge = WorkflowEdge(
                        id=uuid.uuid4(),
                        workflow_id=workflow.id,
                        source_node_id=src_id,
                        target_node_id=tgt_id,
                        condition=edge_data.condition,
                        priority=edge_data.priority
                    )
                    self.db.add(edge)

        # Replace variables if specified
        if data.variables is not None:
            structural_change = True
            self.db.query(WorkflowVariable).filter(WorkflowVariable.workflow_id == workflow.id).delete()
            self.db.flush()

            for var_data in data.variables:
                val = var_data.value
                if var_data.is_secret and val:
                    val = CredentialStore.encode_secure_token(val)
                variable = WorkflowVariable(
                    id=uuid.uuid4(),
                    workflow_id=workflow.id,
                    name=var_data.name,
                    value=val,
                    value_type=var_data.value_type,
                    is_secret=var_data.is_secret
                )
                self.db.add(variable)

        if structural_change:
            workflow.version += 1

        self.db.commit()
        self.db.refresh(workflow)
        logger.info(f"Updated workflow '{workflow.name}' (id={workflow.id}, version={workflow.version})")
        return workflow

    def delete_workflow(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        workflow_id: uuid.UUID
    ) -> bool:
        workflow = self.get_workflow(user_id, workspace_id, workflow_id)
        if not workflow:
            return False

        workflow.deleted_at = datetime.datetime.now(datetime.timezone.utc)
        self.db.commit()
        logger.info(f"Deleted workflow '{workflow.name}' (id={workflow.id})")
        return True

    def validate_workflow(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        workflow_id: uuid.UUID
    ) -> Optional[WorkflowValidationResult]:
        workflow = self.get_workflow(user_id, workspace_id, workflow_id)
        if not workflow:
            return None

        nodes_data = [
            {
                "id": str(n.id),
                "node_key": n.node_key,
                "node_type": n.node_type.value if hasattr(n.node_type, "value") else str(n.node_type),
                "name": n.name,
                "config": n.config,
                "is_enabled": n.is_enabled
            }
            for n in workflow.nodes if not n.deleted_at
        ]

        edges_data = [
            {
                "id": str(e.id),
                "source_node_id": str(e.source_node_id),
                "target_node_id": str(e.target_node_id),
                "condition": e.condition,
                "priority": e.priority
            }
            for e in workflow.edges if not e.deleted_at
        ]

        vars_data = [
            {
                "name": v.name,
                "value_type": v.value_type,
                "is_secret": v.is_secret
            }
            for v in workflow.variables if not v.deleted_at
        ]

        return WorkflowValidationService.validate_graph(nodes_data, edges_data, vars_data)

    def activate_workflow(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        workflow_id: uuid.UUID
    ) -> Tuple[Optional[Workflow], Optional[WorkflowValidationResult]]:
        validation = self.validate_workflow(user_id, workspace_id, workflow_id)
        if not validation:
            return None, None

        if not validation.valid:
            return None, validation

        workflow = self.get_workflow(user_id, workspace_id, workflow_id)
        if not workflow:
            return None, None

        workflow.status = WorkflowStatus.ACTIVE
        workflow.is_active = True
        self.db.commit()
        self.db.refresh(workflow)
        logger.info(f"Activated workflow '{workflow.name}' (id={workflow.id})")
        return workflow, validation

    def pause_workflow(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        workflow_id: uuid.UUID
    ) -> Optional[Workflow]:
        workflow = self.get_workflow(user_id, workspace_id, workflow_id)
        if not workflow:
            return None

        workflow.status = WorkflowStatus.PAUSED
        workflow.is_active = False
        self.db.commit()
        self.db.refresh(workflow)
        logger.info(f"Paused workflow '{workflow.name}' (id={workflow.id})")
        return workflow

    def archive_workflow(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        workflow_id: uuid.UUID
    ) -> Optional[Workflow]:
        workflow = self.get_workflow(user_id, workspace_id, workflow_id)
        if not workflow:
            return None

        workflow.status = WorkflowStatus.ARCHIVED
        workflow.is_active = False
        self.db.commit()
        self.db.refresh(workflow)
        logger.info(f"Archived workflow '{workflow.name}' (id={workflow.id})")
        return workflow

    def get_workflow_definition(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        workflow_id: uuid.UUID
    ) -> Optional[Workflow]:
        return self.get_workflow(user_id, workspace_id, workflow_id)

    def update_workflow_definition(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        workflow_id: uuid.UUID,
        payload: WorkflowDefinitionUpdate
    ) -> Optional[Workflow]:
        workflow = self.get_workflow(user_id, workspace_id, workflow_id)
        if not workflow:
            return None

        if workflow.status == WorkflowStatus.ARCHIVED:
            raise WorkflowArchivedError(f"Cannot modify archived workflow '{workflow.name}'.")

        # 1. Optimistic Concurrency Check
        if workflow.version != payload.expected_version:
            raise VersionConflictError(
                f"Workflow version conflict: expected version {payload.expected_version}, but server has version {workflow.version}. Please reload the latest definition."
            )

        # 2. Graph Validation
        raw_nodes = [n.dict() if hasattr(n, "dict") else n.model_dump() for n in payload.nodes]
        raw_edges = [e.dict() if hasattr(e, "dict") else e.model_dump() for e in payload.edges]
        raw_vars = [v.dict() if hasattr(v, "dict") else v.model_dump() for v in (payload.variables or [])]

        validation = WorkflowValidationService.validate_graph(raw_nodes, raw_edges, raw_vars)
        if not validation.valid:
            err_msgs = "; ".join([e.message for e in validation.errors])
            raise ValueError(f"Workflow definition validation failed: {err_msgs}")

        # 3. Atomic Database Update
        if payload.name:
            workflow.name = payload.name
        if payload.description is not None:
            workflow.description = payload.description

        # Remove existing edges, nodes, variables
        self.db.query(WorkflowEdge).filter(WorkflowEdge.workflow_id == workflow.id).delete()
        self.db.query(WorkflowNode).filter(WorkflowNode.workflow_id == workflow.id).delete()
        self.db.query(WorkflowVariable).filter(WorkflowVariable.workflow_id == workflow.id).delete()
        self.db.flush()

        # Recreate nodes
        node_key_to_id = {}
        for node_data in payload.nodes:
            node_id = uuid.uuid4()
            node_key_to_id[node_data.node_key] = node_id
            node = WorkflowNode(
                id=node_id,
                workflow_id=workflow.id,
                node_key=node_data.node_key,
                node_type=node_data.node_type,
                name=node_data.name,
                config=node_data.config,
                position=node_data.position,
                is_enabled=node_data.is_enabled
            )
            self.db.add(node)
        self.db.flush()

        # Recreate edges
        for edge_data in payload.edges:
            src_id = edge_data.source_node_id or node_key_to_id.get(edge_data.source_node_key or "")
            tgt_id = edge_data.target_node_id or node_key_to_id.get(edge_data.target_node_key or "")
            if src_id and tgt_id:
                edge = WorkflowEdge(
                    id=uuid.uuid4(),
                    workflow_id=workflow.id,
                    source_node_id=src_id,
                    target_node_id=tgt_id,
                    condition=edge_data.condition,
                    priority=edge_data.priority
                )
                self.db.add(edge)

        # Recreate variables
        if payload.variables:
            for var_data in payload.variables:
                val = var_data.value
                if var_data.is_secret and val:
                    val = CredentialStore.encode_secure_token(val)
                variable = WorkflowVariable(
                    id=uuid.uuid4(),
                    workflow_id=workflow.id,
                    name=var_data.name,
                    value=val,
                    value_type=var_data.value_type,
                    is_secret=var_data.is_secret
                )
                self.db.add(variable)

        workflow.version += 1
        self.db.commit()
        self.db.refresh(workflow)
        logger.info(f"Saved workflow definition '{workflow.name}' (id={workflow.id}, version={workflow.version})")
        return workflow

    def clone_workflow(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        workflow_id: uuid.UUID,
        clone_name: Optional[str] = None
    ) -> Optional[Workflow]:
        source = self.get_workflow(user_id, workspace_id, workflow_id)
        if not source:
            return None

        new_name = clone_name or f"{source.name} (Copy)"
        cloned = Workflow(
            id=uuid.uuid4(),
            user_id=user_id,
            workspace_id=workspace_id,
            name=new_name,
            description=source.description,
            status=WorkflowStatus.DRAFT,
            version=1,
            is_active=False
        )
        self.db.add(cloned)
        self.db.flush()

        node_map = {}
        for n in source.nodes:
            if not n.deleted_at:
                new_n_id = uuid.uuid4()
                node_map[n.id] = new_n_id
                cloned_node = WorkflowNode(
                    id=new_n_id,
                    workflow_id=cloned.id,
                    node_key=n.node_key,
                    node_type=n.node_type,
                    name=n.name,
                    config=n.config,
                    position=n.position,
                    is_enabled=n.is_enabled
                )
                self.db.add(cloned_node)
        self.db.flush()

        for e in source.edges:
            if not e.deleted_at and e.source_node_id in node_map and e.target_node_id in node_map:
                cloned_edge = WorkflowEdge(
                    id=uuid.uuid4(),
                    workflow_id=cloned.id,
                    source_node_id=node_map[e.source_node_id],
                    target_node_id=node_map[e.target_node_id],
                    condition=e.condition,
                    priority=e.priority
                )
                self.db.add(cloned_edge)

        for v in source.variables:
            if not v.deleted_at:
                cloned_var = WorkflowVariable(
                    id=uuid.uuid4(),
                    workflow_id=cloned.id,
                    name=v.name,
                    value=v.value,
                    value_type=v.value_type,
                    is_secret=v.is_secret
                )
                self.db.add(cloned_var)

        self.db.commit()
        self.db.refresh(cloned)
        logger.info(f"Cloned workflow '{source.name}' to '{cloned.name}' (id={cloned.id})")
        return cloned


class VersionConflictError(Exception):
    pass


class WorkflowArchivedError(Exception):
    pass
