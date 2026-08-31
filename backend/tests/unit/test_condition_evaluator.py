import pytest
import uuid
from app.services.condition_evaluator import ConditionEvaluator
from app.services.workflow_execution import WorkflowExecutionContext

@pytest.fixture
def sample_context():
    return WorkflowExecutionContext(
        execution_id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        workflow_version=1,
        user_id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        input_data={"age": 25, "score": 88.5, "role": "admin", "tags": ["lead", "ai"], "meta": {"country": "India"}},
        variables={"stage": "production", "max_limit": 100},
        node_outputs={"agent_1": {"output": {"verdict": "APPROVED", "confidence": 0.95}}}
    )

def test_all_comparison_operators(sample_context):
    # equals & not_equals
    assert ConditionEvaluator.evaluate({"left": "{{input.role}}", "operator": "equals", "right": "admin"}, sample_context)["result"] is True
    assert ConditionEvaluator.evaluate({"left": "{{input.role}}", "operator": "not_equals", "right": "guest"}, sample_context)["result"] is True

    # numeric comparisons
    assert ConditionEvaluator.evaluate({"left": "{{input.age}}", "operator": "greater_than", "right": 18}, sample_context)["result"] is True
    assert ConditionEvaluator.evaluate({"left": "{{input.age}}", "operator": "less_than", "right": 30}, sample_context)["result"] is True
    assert ConditionEvaluator.evaluate({"left": "{{input.score}}", "operator": "greater_or_equal", "right": 88.5}, sample_context)["result"] is True
    assert ConditionEvaluator.evaluate({"left": "{{input.score}}", "operator": "less_or_equal", "right": 88.5}, sample_context)["result"] is True

    # contains & not_contains
    assert ConditionEvaluator.evaluate({"left": "{{input.tags}}", "operator": "contains", "right": "ai"}, sample_context)["result"] is True
    assert ConditionEvaluator.evaluate({"left": "{{input.tags}}", "operator": "not_contains", "right": "finance"}, sample_context)["result"] is True

    # in & not_in
    assert ConditionEvaluator.evaluate({"left": "admin", "operator": "in", "right": ["user", "admin"]}, sample_context)["result"] is True
    assert ConditionEvaluator.evaluate({"left": "guest", "operator": "not_in", "right": ["user", "admin"]}, sample_context)["result"] is True

    # starts_with & ends_with
    assert ConditionEvaluator.evaluate({"left": "{{input.role}}", "operator": "starts_with", "right": "adm"}, sample_context)["result"] is True
    assert ConditionEvaluator.evaluate({"left": "{{input.role}}", "operator": "ends_with", "right": "min"}, sample_context)["result"] is True

    # exists & not_exists
    assert ConditionEvaluator.evaluate({"left": "{{input.meta.country}}", "operator": "exists"}, sample_context)["result"] is True
    assert ConditionEvaluator.evaluate({"left": "{{input.missing_field}}", "operator": "not_exists"}, sample_context)["result"] is True

def test_compound_condition_groups(sample_context):
    # AND logic
    and_group = {
        "logic": "AND",
        "conditions": [
            {"left": "{{input.age}}", "operator": "greater_than", "right": 20},
            {"left": "{{nodes.agent_1.output.verdict}}", "operator": "equals", "right": "APPROVED"}
        ]
    }
    assert ConditionEvaluator.evaluate(and_group, sample_context)["result"] is True

    # OR logic
    or_group = {
        "logic": "OR",
        "conditions": [
            {"left": "{{input.age}}", "operator": "less_than", "right": 18}, # False
            {"left": "{{input.role}}", "operator": "equals", "right": "admin"} # True
        ]
    }
    assert ConditionEvaluator.evaluate(or_group, sample_context)["result"] is True

    # NOT logic
    not_group = {
        "logic": "NOT",
        "conditions": [
            {"left": "{{input.age}}", "operator": "less_than", "right": 18} # False -> NOT makes it True
        ]
    }
    assert ConditionEvaluator.evaluate(not_group, sample_context)["result"] is True

def test_nested_condition_trees(sample_context):
    # (age >= 21 AND role == admin) OR (score > 90 AND stage == production)
    nested_group = {
        "logic": "OR",
        "conditions": [
            {
                "logic": "AND",
                "conditions": [
                    {"left": "{{input.age}}", "operator": "greater_or_equal", "right": 21},
                    {"left": "{{input.role}}", "operator": "equals", "right": "admin"}
                ]
            },
            {
                "logic": "AND",
                "conditions": [
                    {"left": "{{input.score}}", "operator": "greater_than", "right": 90},
                    {"left": "{{variables.stage}}", "operator": "equals", "right": "production"}
                ]
            }
        ]
    }
    res = ConditionEvaluator.evaluate(nested_group, sample_context)
    assert res["result"] is True
    assert res["logic"] == "OR"
    assert res["evaluated_conditions"] == 2
