import uuid
import re
import json
import datetime
from collections import defaultdict, deque
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
from loguru import logger
from pydantic import BaseModel, Field

from app.models.workflow import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkflowVariable,
    WorkflowExecution,
    WorkflowExecutionNode,
    WorkflowStatus,
    WorkflowExecutionStatus,
    WorkflowNodeStatus,
    WorkflowNodeType
)
from app.services.workflow_validation import WorkflowValidationService
from app.core.mcp.security import CredentialStore

VAR_REF_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_\.\-]+)\s*\}\}")

class WorkflowExecutionContext(BaseModel):
    """
    Typed runtime execution context for an active workflow execution instance.
    Holds tenant boundaries, resolved inputs, variables, and accumulated node outputs.
    """
    execution_id: uuid.UUID
    workflow_id: uuid.UUID
    workflow_version: int
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    input_data: Dict[str, Any] = Field(default_factory=dict)
    variables: Dict[str, Any] = Field(default_factory=dict)
    node_outputs: Dict[str, Any] = Field(default_factory=dict)
    current_node: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def resolve_expression(self, text: Optional[str]) -> Any:
        """
        Safely resolves {{input.x}}, {{variables.y}}, and {{nodes.z.output}} references.
        No eval() or dynamic code execution.
        """
        if not text or not isinstance(text, str):
            return text

        def replacer(match):
            path = match.group(1).strip().split(".")
            root = path[0]

            if root == "input":
                curr = self.input_data
                for p in path[1:]:
                    if isinstance(curr, dict):
                        curr = curr.get(p)
                    else:
                        return ""
                return str(curr) if curr is not None else ""

            elif root == "variables":
                if len(path) > 1:
                    var_name = path[1]
                    val = self.variables.get(var_name)
                    return str(val) if val is not None else ""
                return ""

            elif root == "nodes":
                if len(path) > 1:
                    node_key = path[1]
                    curr = self.node_outputs.get(node_key)
                    subpath = path[2:]
                    if subpath and subpath[0] == "output" and isinstance(curr, dict) and "output" not in curr:
                        subpath = subpath[1:]
                    for p in subpath:
                        if isinstance(curr, dict):
                            curr = curr.get(p)
                        else:
                            return ""
                    return str(curr) if curr is not None else ""
                return ""

            return match.group(0)

        # If text is exactly a single reference (e.g. "{{input.data}}"), return exact typed value if possible
        full_match = re.fullmatch(r"\{\{\s*([a-zA-Z0-9_\.\-]+)\s*\}\}", text.strip())
        if full_match:
            path = full_match.group(1).strip().split(".")
            root = path[0]
            if root == "input":
                curr = self.input_data
                for p in path[1:]:
                    if isinstance(curr, dict):
                        curr = curr.get(p)
                    else:
                        return None
                return curr
            elif root == "variables":
                if len(path) > 1:
                    return self.variables.get(path[1])
            elif root == "nodes":
                if len(path) > 1:
                    curr = self.node_outputs.get(path[1])
                    subpath = path[2:]
                    if subpath and subpath[0] == "output" and isinstance(curr, dict) and "output" not in curr:
                        subpath = subpath[1:]
                    for p in subpath:
                        if isinstance(curr, dict):
                            curr = curr.get(p)
                        else:
                            return None
                    return curr

        return VAR_REF_PATTERN.sub(replacer, text)


class WorkflowExecutionService:
    """
    Foundation Execution Engine for AegisAI Workflows.
    Manages immutable snapshots, deterministic topological DAG progression,
    per-node execution tracking, variable resolution, and state transitions.
    """
    def __init__(self, db: Session):
        self.db = db

    def create_snapshot(self, workflow: Workflow) -> Dict[str, Any]:
        """Creates a deterministic JSON snapshot of the workflow graph and variables."""
        return {
            "workflow_id": str(workflow.id),
            "version": workflow.version,
            "name": workflow.name,
            "nodes": [
                {
                    "id": str(n.id),
                    "node_key": n.node_key,
                    "node_type": n.node_type.value if hasattr(n.node_type, "value") else str(n.node_type),
                    "name": n.name,
                    "config": n.config,
                    "position": n.position,
                    "is_enabled": n.is_enabled
                }
                for n in workflow.nodes if not n.deleted_at
            ],
            "edges": [
                {
                    "id": str(e.id),
                    "source_node_id": str(e.source_node_id),
                    "target_node_id": str(e.target_node_id),
                    "condition": e.condition,
                    "priority": e.priority
                }
                for e in workflow.edges if not e.deleted_at
            ],
            "variables": [
                {
                    "name": v.name,
                    "value": v.value if not v.is_secret else CredentialStore.decode_secure_token(v.value or ""),
                    "value_type": v.value_type,
                    "is_secret": v.is_secret
                }
                for v in workflow.variables if not v.deleted_at
            ]
        }

    def compute_topological_order(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Computes deterministic execution order of nodes using Kahn's algorithm,
        breaking ties by edge priority then node_key.
        """
        nodes = snapshot.get("nodes", [])
        edges = snapshot.get("edges", [])

        node_id_to_node = {n["id"]: n for n in nodes if n.get("is_enabled", True)}
        node_key_to_id = {n["node_key"]: n["id"] for n in nodes}

        # Build adjacency and in-degree
        adj = defaultdict(list)
        in_degree = {n_id: 0 for n_id in node_id_to_node}

        for edge in edges:
            src = edge["source_node_id"]
            tgt = edge["target_node_id"]
            if src in node_id_to_node and tgt in node_id_to_node:
                prio = edge.get("priority", 0)
                adj[src].append((prio, node_id_to_node[tgt]["node_key"], tgt))
                in_degree[tgt] += 1

        # Queue of nodes with 0 in-degree, sorted by START type first then node_key
        zero_in_degree = [n_id for n_id, deg in in_degree.items() if deg == 0]
        zero_in_degree.sort(
            key=lambda n_id: (
                0 if node_id_to_node[n_id]["node_type"] == WorkflowNodeType.START.value else 1,
                node_id_to_node[n_id]["node_key"]
            )
        )

        q = deque(zero_in_degree)
        order = []

        while q:
            curr_id = q.popleft()
            order.append(node_id_to_node[curr_id])

            # Sort outgoing neighbors by priority desc, then target node_key asc
            neighbors = sorted(adj[curr_id], key=lambda item: (-item[0], item[1]))
            for prio, key, tgt_id in neighbors:
                in_degree[tgt_id] -= 1
                if in_degree[tgt_id] == 0:
                    q.append(tgt_id)

        return order

    def execute_workflow(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        workflow_id: uuid.UUID,
        input_data: Optional[Dict[str, Any]] = None
    ) -> WorkflowExecution:
        workflow = self.db.query(Workflow).filter(
            and_(
                Workflow.id == workflow_id,
                Workflow.workspace_id == workspace_id,
                Workflow.deleted_at.is_(None)
            )
        ).first()

        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found in active workspace.")

        # Validate workflow before running
        snapshot = self.create_snapshot(workflow)
        validation = WorkflowValidationService.validate_graph(
            snapshot["nodes"],
            snapshot["edges"],
            snapshot["variables"]
        )
        if not validation.valid:
            err_msgs = "; ".join([e.message for e in validation.errors])
            raise ValueError(f"Cannot execute invalid workflow: {err_msgs}")

        # Initialize execution record
        execution = WorkflowExecution(
            id=uuid.uuid4(),
            workflow_id=workflow.id,
            workflow_version=workflow.version,
            user_id=user_id,
            workspace_id=workspace_id,
            status=WorkflowExecutionStatus.RUNNING,
            input_data=input_data or {},
            snapshot=snapshot,
            started_at=datetime.datetime.now(datetime.timezone.utc)
        )
        self.db.add(execution)
        self.db.flush()

        # Build context
        variables_dict = {
            v["name"]: v["value"]
            for v in snapshot["variables"]
        }
        context = WorkflowExecutionContext(
            execution_id=execution.id,
            workflow_id=workflow.id,
            workflow_version=workflow.version,
            user_id=user_id,
            workspace_id=workspace_id,
            input_data=input_data or {},
            variables=variables_dict,
            node_outputs={}
        )

        ordered_nodes = self.compute_topological_order(snapshot)
        logger.info(f"Executing workflow '{workflow.name}' ({len(ordered_nodes)} nodes in sequence)")

        final_output = None
        has_error = False
        error_message = None

        for node_def in ordered_nodes:
            node_id = uuid.UUID(node_def["id"])
            node_key = node_def["node_key"]
            node_type = node_def["node_type"]
            config = node_def.get("config", {})

            context.current_node = node_key

            exec_node = WorkflowExecutionNode(
                id=uuid.uuid4(),
                execution_id=execution.id,
                node_id=node_id,
                node_key=node_key,
                status=WorkflowNodeStatus.RUNNING,
                input_data=context.input_data if node_type == WorkflowNodeType.START.value else context.node_outputs,
                started_at=datetime.datetime.now(datetime.timezone.utc)
            )
            self.db.add(exec_node)
            self.db.flush()

            try:
                # Dispatch node execution foundation behavior
                node_out = self._execute_node_foundation(node_type, config, context)
                context.node_outputs[node_key] = node_out

                exec_node.status = WorkflowNodeStatus.COMPLETED
                exec_node.output_data = node_out
                exec_node.completed_at = datetime.datetime.now(datetime.timezone.utc)
                self.db.flush()

                if node_type == WorkflowNodeType.END.value:
                    final_output = node_out

            except Exception as e:
                logger.error(f"Error executing workflow node '{node_key}': {e}")
                exec_node.status = WorkflowNodeStatus.FAILED
                exec_node.error = str(e)
                exec_node.completed_at = datetime.datetime.now(datetime.timezone.utc)
                self.db.flush()

                has_error = True
                error_message = f"Node '{node_key}' failed: {str(e)}"
                break

        if has_error:
            execution.status = WorkflowExecutionStatus.FAILED
            execution.error = error_message
        else:
            execution.status = WorkflowExecutionStatus.COMPLETED
            execution.output_data = final_output or context.node_outputs

        execution.completed_at = datetime.datetime.now(datetime.timezone.utc)
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def _execute_node_foundation(
        self,
        node_type: str,
        config: Dict[str, Any],
        context: WorkflowExecutionContext
    ) -> Dict[str, Any]:
        """
        Executes node logic. In Phase 7.1, START, TRANSFORM, and END nodes execute cleanly;
        AI/MCP/RAG/GRAPH/MEMORY/TOOL nodes report clean foundation results ready for Phase 7.2+.
        """
        if node_type == WorkflowNodeType.START.value:
            return {"status": "SUCCESS", "data": context.input_data}

        elif node_type == WorkflowNodeType.TRANSFORM.value:
            mapping = config.get("mapping", {})
            transformed = {}
            for k, expr in mapping.items():
                transformed[k] = context.resolve_expression(expr)
            return {"status": "SUCCESS", "transformed": transformed}

        elif node_type == WorkflowNodeType.END.value:
            template = config.get("output_template")
            if template:
                resolved = context.resolve_expression(template)
                return {"status": "SUCCESS", "result": resolved}
            return {"status": "SUCCESS", "result": "Execution reached END node"}

        else:
            # Foundation placeholder for agent / mcp / rag / graph / memory nodes
            return {
                "status": "NOT_IMPLEMENTED_IN_7_1",
                "node_type": node_type,
                "config_summary": {k: v for k, v in config.items() if not str(k).lower().startswith("secret")}
            }

    def cancel_execution(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        execution_id: uuid.UUID
    ) -> Optional[WorkflowExecution]:
        execution = self.db.query(WorkflowExecution).filter(
            and_(
                WorkflowExecution.id == execution_id,
                WorkflowExecution.workspace_id == workspace_id,
                WorkflowExecution.deleted_at.is_(None)
            )
        ).first()
        if not execution:
            return None

        if execution.status in (WorkflowExecutionStatus.RUNNING, WorkflowExecutionStatus.PENDING, WorkflowExecutionStatus.WAITING):
            execution.status = WorkflowExecutionStatus.CANCELLED
            execution.completed_at = datetime.datetime.now(datetime.timezone.utc)
            self.db.commit()
            self.db.refresh(execution)
            logger.info(f"Cancelled workflow execution {execution_id}")

        return execution

    def get_execution(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        execution_id: uuid.UUID
    ) -> Optional[WorkflowExecution]:
        return self.db.query(WorkflowExecution).filter(
            and_(
                WorkflowExecution.id == execution_id,
                WorkflowExecution.workspace_id == workspace_id,
                WorkflowExecution.deleted_at.is_(None)
            )
        ).first()

    def list_executions(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        workflow_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[WorkflowExecution], int]:
        query = self.db.query(WorkflowExecution).filter(
            and_(
                WorkflowExecution.workspace_id == workspace_id,
                WorkflowExecution.deleted_at.is_(None)
            )
        )
        if workflow_id:
            query = query.filter(WorkflowExecution.workflow_id == workflow_id)

        total = query.count()
        executions = query.order_by(WorkflowExecution.created_at.desc()).offset(offset).limit(limit).all()
        return executions, total
