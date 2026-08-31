import pytest
from app.services.workflow_validation import WorkflowValidationService
from app.models.workflow import WorkflowNodeType

def test_valid_dag_validation():
    nodes = [
        {"node_key": "start_1", "node_type": "start", "name": "Start", "config": {}},
        {"node_key": "transform_1", "node_type": "transform", "name": "Transform", "config": {"mapping": {}}},
        {"node_key": "end_1", "node_type": "end", "name": "End", "config": {}}
    ]
    edges = [
        {"source_node_key": "start_1", "target_node_key": "transform_1"},
        {"source_node_key": "transform_1", "target_node_key": "end_1"}
    ]
    res = WorkflowValidationService.validate_graph(nodes, edges)
    assert res.valid is True
    assert len(res.errors) == 0

def test_missing_and_multiple_start_nodes():
    # Missing START
    nodes_no_start = [
        {"node_key": "end_1", "node_type": "end", "name": "End", "config": {}}
    ]
    res1 = WorkflowValidationService.validate_graph(nodes_no_start, [])
    assert res1.valid is False
    assert any(e.code == "MISSING_START_NODE" for e in res1.errors)

    # Multiple START
    nodes_multi_start = [
        {"node_key": "start_1", "node_type": "start", "name": "Start 1", "config": {}},
        {"node_key": "start_2", "node_type": "start", "name": "Start 2", "config": {}},
        {"node_key": "end_1", "node_type": "end", "name": "End", "config": {}}
    ]
    res2 = WorkflowValidationService.validate_graph(nodes_multi_start, [])
    assert res2.valid is False
    assert any(e.code == "MULTIPLE_START_NODES" for e in res2.errors)

def test_missing_end_node():
    nodes_no_end = [
        {"node_key": "start_1", "node_type": "start", "name": "Start", "config": {}}
    ]
    res = WorkflowValidationService.validate_graph(nodes_no_end, [])
    assert res.valid is False
    assert any(e.code == "MISSING_END_NODE" for e in res.errors)

def test_duplicate_node_key_rejection():
    nodes = [
        {"node_key": "dup_key", "node_type": "start", "name": "Start", "config": {}},
        {"node_key": "dup_key", "node_type": "end", "name": "End", "config": {}}
    ]
    res = WorkflowValidationService.validate_graph(nodes, [])
    assert res.valid is False
    assert any(e.code == "DUPLICATE_NODE_KEY" for e in res.errors)

def test_self_loop_rejection():
    nodes = [
        {"node_key": "start_1", "node_type": "start", "name": "Start", "config": {}},
        {"node_key": "end_1", "node_type": "end", "name": "End", "config": {}}
    ]
    edges = [
        {"source_node_key": "start_1", "target_node_key": "start_1"}
    ]
    res = WorkflowValidationService.validate_graph(nodes, edges)
    assert res.valid is False
    assert any(e.code == "SELF_LOOP_DETECTED" for e in res.errors)

def test_cycle_detection_in_dag():
    nodes = [
        {"node_key": "start_1", "node_type": "start", "name": "Start", "config": {}},
        {"node_key": "node_a", "node_type": "transform", "name": "Node A", "config": {}},
        {"node_key": "node_b", "node_type": "transform", "name": "Node B", "config": {}},
        {"node_key": "end_1", "node_type": "end", "name": "End", "config": {}}
    ]
    edges = [
        {"source_node_key": "start_1", "target_node_key": "node_a"},
        {"source_node_key": "node_a", "target_node_key": "node_b"},
        {"source_node_key": "node_b", "target_node_key": "node_a"},  # Cycle: A -> B -> A
        {"source_node_key": "node_b", "target_node_key": "end_1"}
    ]
    res = WorkflowValidationService.validate_graph(nodes, edges)
    assert res.valid is False
    assert any(e.code == "CYCLE_DETECTED" for e in res.errors)

def test_unreachable_node_warning():
    nodes = [
        {"node_key": "start_1", "node_type": "start", "name": "Start", "config": {}},
        {"node_key": "end_1", "node_type": "end", "name": "End", "config": {}},
        {"node_key": "orphan_1", "node_type": "agent", "name": "Orphan", "config": {}}
    ]
    edges = [
        {"source_node_key": "start_1", "target_node_key": "end_1"}
    ]
    res = WorkflowValidationService.validate_graph(nodes, edges)
    assert res.valid is True
    assert any(w.code == "UNREACHABLE_NODE" for w in res.warnings)
