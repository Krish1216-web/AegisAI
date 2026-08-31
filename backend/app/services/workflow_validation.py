import uuid
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict, deque

from app.models.workflow import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkflowVariable,
    WorkflowNodeType
)
from app.schemas.workflow import (
    WorkflowValidationResult,
    WorkflowValidationItem,
    StartNodeConfig,
    EndNodeConfig,
    AgentNodeConfig,
    RAGNodeConfig,
    GraphNodeConfig,
    MemoryNodeConfig,
    MCPToolNodeConfig,
    MCPResourceNodeConfig,
    MCPPromptNodeConfig,
    LocalToolNodeConfig,
    ConditionNodeConfig,
    HumanApprovalNodeConfig,
    TransformNodeConfig
)
from app.services.condition_evaluator import ConditionEvaluator

NODE_CONFIG_VALIDATORS = {
    WorkflowNodeType.START: StartNodeConfig,
    WorkflowNodeType.END: EndNodeConfig,
    WorkflowNodeType.AGENT: AgentNodeConfig,
    WorkflowNodeType.RAG: RAGNodeConfig,
    WorkflowNodeType.GRAPH: GraphNodeConfig,
    WorkflowNodeType.MEMORY: MemoryNodeConfig,
    WorkflowNodeType.MCP_TOOL: MCPToolNodeConfig,
    WorkflowNodeType.MCP_RESOURCE: MCPResourceNodeConfig,
    WorkflowNodeType.MCP_PROMPT: MCPPromptNodeConfig,
    WorkflowNodeType.LOCAL_TOOL: LocalToolNodeConfig,
    WorkflowNodeType.CONDITION: ConditionNodeConfig,
    WorkflowNodeType.HUMAN_APPROVAL: HumanApprovalNodeConfig,
    WorkflowNodeType.TRANSFORM: TransformNodeConfig,
}

class WorkflowValidationService:
    """
    Deterministic DAG and structural validator for workflow graphs.
    Enforces START/END node rules, unique node keys, valid edges, reachability,
    cycle prohibition, and node configuration correctness.
    """

    @classmethod
    def validate_graph(
        cls,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        variables: Optional[List[Dict[str, Any]]] = None
    ) -> WorkflowValidationResult:
        errors: List[WorkflowValidationItem] = []
        warnings: List[WorkflowValidationItem] = []

        if not nodes:
            errors.append(WorkflowValidationItem(
                code="EMPTY_WORKFLOW",
                message="Workflow contains no nodes."
            ))
            return WorkflowValidationResult(valid=False, errors=errors, warnings=warnings)

        # 1. Node Key Uniqueness & Mapping
        node_keys_seen: Set[str] = set()
        node_id_to_key: Dict[str, str] = {}
        node_key_to_data: Dict[str, Dict[str, Any]] = {}
        start_nodes: List[str] = []
        end_nodes: List[str] = []

        for node in nodes:
            key = node.get("node_key")
            n_id = str(node.get("id")) if node.get("id") else None
            n_type_raw = node.get("node_type")

            if not key or not str(key).strip():
                errors.append(WorkflowValidationItem(
                    code="INVALID_NODE_KEY",
                    message="Node must have a non-empty node_key."
                ))
                continue

            if key in node_keys_seen:
                errors.append(WorkflowValidationItem(
                    code="DUPLICATE_NODE_KEY",
                    message=f"Duplicate node_key '{key}' found.",
                    node_key=key
                ))
            else:
                node_keys_seen.add(key)

            if n_id:
                node_id_to_key[n_id] = key

            node_key_to_data[key] = node

            # Match enum
            try:
                n_type = WorkflowNodeType(n_type_raw) if isinstance(n_type_raw, str) else n_type_raw
            except ValueError:
                errors.append(WorkflowValidationItem(
                    code="INVALID_NODE_TYPE",
                    message=f"Unsupported node_type '{n_type_raw}' on node '{key}'.",
                    node_key=key
                ))
                continue

            if n_type == WorkflowNodeType.START:
                start_nodes.append(key)
            elif n_type == WorkflowNodeType.END:
                end_nodes.append(key)

            # Node config validation
            config = node.get("config") or {}
            validator_cls = NODE_CONFIG_VALIDATORS.get(n_type)
            if validator_cls:
                try:
                    validator_cls(**config)
                except Exception as e:
                    errors.append(WorkflowValidationItem(
                        code="INVALID_NODE_CONFIG",
                        message=f"Configuration error on node '{key}': {str(e)}",
                        node_key=key
                    ))

            # Deep condition structure validation
            if n_type == WorkflowNodeType.CONDITION and config:
                cond_errs = ConditionEvaluator.validate_structure(config)
                for c_err in cond_errs:
                    errors.append(WorkflowValidationItem(
                        code="INVALID_CONDITION_STRUCTURE",
                        message=f"Condition node '{key}': {c_err}",
                        node_key=key
                    ))

        # 2. START & END node cardinality rules
        if len(start_nodes) == 0:
            errors.append(WorkflowValidationItem(
                code="MISSING_START_NODE",
                message="Workflow must contain exactly one START node."
            ))
        elif len(start_nodes) > 1:
            errors.append(WorkflowValidationItem(
                code="MULTIPLE_START_NODES",
                message=f"Workflow contains multiple START nodes: {', '.join(start_nodes)}."
            ))

        if len(end_nodes) == 0:
            errors.append(WorkflowValidationItem(
                code="MISSING_END_NODE",
                message="Workflow must contain at least one END node."
            ))

        # 3. Edge Integrity & Graph Construction
        adjacency: Dict[str, List[str]] = defaultdict(list)
        in_degree: Dict[str, int] = {key: 0 for key in node_keys_seen}
        edges_seen: Set[str] = set()
        default_edges_count: Dict[str, int] = defaultdict(int)

        for edge in edges:
            # Resolve source/target by key or id
            src = edge.get("source_node_key") or node_id_to_key.get(str(edge.get("source_node_id")))
            tgt = edge.get("target_node_key") or node_id_to_key.get(str(edge.get("target_node_id")))

            if not src or src not in node_keys_seen:
                errors.append(WorkflowValidationItem(
                    code="INVALID_EDGE_SOURCE",
                    message=f"Edge references non-existent source node '{src or edge.get('source_node_id')}'."
                ))
                continue

            if not tgt or tgt not in node_keys_seen:
                errors.append(WorkflowValidationItem(
                    code="INVALID_EDGE_TARGET",
                    message=f"Edge references non-existent target node '{tgt or edge.get('target_node_id')}'."
                ))
                continue

            # Self-loop
            if src == tgt:
                errors.append(WorkflowValidationItem(
                    code="SELF_LOOP_DETECTED",
                    message=f"Self-loop detected on node '{src}'.",
                    node_key=src
                ))
                continue

            # Duplicate edge
            edge_sig = f"{src}->{tgt}"
            if edge_sig in edges_seen:
                errors.append(WorkflowValidationItem(
                    code="DUPLICATE_EDGE",
                    message=f"Duplicate edge detected from '{src}' to '{tgt}'."
                ))
                continue
            edges_seen.add(edge_sig)

            # Edge condition validation
            edge_cond = edge.get("condition")
            if edge_cond:
                if isinstance(edge_cond, dict) and edge_cond.get("is_default") is True:
                    default_edges_count[src] += 1
                    if default_edges_count[src] > 1:
                        errors.append(WorkflowValidationItem(
                            code="MULTIPLE_DEFAULT_EDGES",
                            message=f"Node '{src}' has multiple default fallback outgoing edges.",
                            node_key=src
                        ))
                else:
                    c_errs = ConditionEvaluator.validate_structure(edge_cond)
                    for c_err in c_errs:
                        errors.append(WorkflowValidationItem(
                            code="INVALID_EDGE_CONDITION",
                            message=f"Edge '{src}' -> '{tgt}': {c_err}",
                            node_key=src
                        ))

            adjacency[src].append(tgt)
            in_degree[tgt] += 1

        # 4. Cycle Detection using Kahn's Algorithm (Topological Sort)
        if len(start_nodes) == 1:
            q = deque([k for k, deg in in_degree.items() if deg == 0])
            visited_count = 0
            temp_in_degree = in_degree.copy()

            while q:
                curr = q.popleft()
                visited_count += 1
                for neighbor in adjacency[curr]:
                    temp_in_degree[neighbor] -= 1
                    if temp_in_degree[neighbor] == 0:
                        q.append(neighbor)

            if visited_count < len(node_keys_seen):
                errors.append(WorkflowValidationItem(
                    code="CYCLE_DETECTED",
                    message="Workflow graph contains a cycle or loop. Cyclic workflows are not permitted."
                ))

        # 5. Reachability from START node
        if len(start_nodes) == 1:
            start_key = start_nodes[0]
            reachable_from_start: Set[str] = set()
            bfs_q = deque([start_key])

            while bfs_q:
                curr = bfs_q.popleft()
                if curr not in reachable_from_start:
                    reachable_from_start.add(curr)
                    for neighbor in adjacency[curr]:
                        if neighbor not in reachable_from_start:
                            bfs_q.append(neighbor)

            unreachable = node_keys_seen - reachable_from_start
            for unreach_key in unreachable:
                warnings.append(WorkflowValidationItem(
                    code="UNREACHABLE_NODE",
                    message=f"Node '{unreach_key}' is unreachable from the START node.",
                    node_key=unreach_key
                ))

        # 6. Variable Validation
        if variables:
            var_names_seen: Set[str] = set()
            for var in variables:
                v_name = var.get("name")
                if not v_name or not str(v_name).strip():
                    errors.append(WorkflowValidationItem(
                        code="INVALID_VARIABLE_NAME",
                        message="Workflow variable must have a non-empty name."
                    ))
                elif v_name in var_names_seen:
                    errors.append(WorkflowValidationItem(
                        code="DUPLICATE_VARIABLE_NAME",
                        message=f"Duplicate variable name '{v_name}'."
                    ))
                else:
                    var_names_seen.add(v_name)

        is_valid = len(errors) == 0
        return WorkflowValidationResult(valid=is_valid, errors=errors, warnings=warnings)
