import pytest
from app.services.condition_evaluator import ConditionEvaluator
from app.services.workflow_validation import WorkflowValidationService

def test_condition_evaluator_validation_rules():
    # Valid condition
    assert len(ConditionEvaluator.validate_structure({"left": "a", "operator": "equals", "right": "b"})) == 0

    # Invalid comparison operator
    errs = ConditionEvaluator.validate_structure({"left": "a", "operator": "is_similar_to", "right": "b"})
    assert any("Invalid comparison operator" in e for e in errs)

    # Invalid logic operator
    errs_logic = ConditionEvaluator.validate_structure({"logic": "XOR", "conditions": [{"left": "a", "operator": "equals", "right": "b"}]})
    assert any("Invalid logic operator" in e for e in errs_logic)

    # Empty conditions list
    errs_empty = ConditionEvaluator.validate_structure({"logic": "AND", "conditions": []})
    assert any("cannot be empty" in e for e in errs_empty)

    # NOT with more than 1 child
    errs_not = ConditionEvaluator.validate_structure({
        "logic": "NOT",
        "conditions": [
            {"left": "a", "operator": "equals", "right": "b"},
            {"left": "c", "operator": "equals", "right": "d"}
        ]
    })
    assert any("requires exactly 1 child" in e for e in errs_not)

def test_workflow_validation_rejects_malformed_conditions_and_multiple_defaults():
    nodes = [
        {"node_key": "s1", "node_type": "start", "config": {}},
        {"node_key": "c1", "node_type": "condition", "config": {"left": "x", "operator": "invalid_op", "right": "y"}},
        {"node_key": "e1", "node_type": "end", "config": {}}
    ]
    edges = [
        {"source_node_key": "s1", "target_node_key": "c1"},
        {"source_node_key": "c1", "target_node_key": "e1", "condition": {"is_default": True}},
        {"source_node_key": "c1", "target_node_key": "e1", "condition": {"is_default": True}} # Duplicate edge + multiple defaults
    ]

    res = WorkflowValidationService.validate_graph(nodes, edges)
    assert res.valid is False
    codes = [e.code for e in res.errors]
    assert "INVALID_CONDITION_STRUCTURE" in codes or "INVALID_EDGE_CONDITION" in codes or "MULTIPLE_DEFAULT_EDGES" in codes
