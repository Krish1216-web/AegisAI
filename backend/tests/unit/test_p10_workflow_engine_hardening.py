import uuid
import pytest
from app.services.condition_evaluator import ConditionEvaluator

def test_condition_evaluator_type_safety():
    evaluator = ConditionEvaluator()
    
    # Numeric comparison with valid types
    assert evaluator.evaluate_leaf("greater_than", 50, 20) is True
    assert evaluator.evaluate_leaf("greater_or_equal", 10, 20) is False
    assert evaluator.evaluate_leaf("less_than", 15, 30) is True
    
    # String contains
    assert evaluator.evaluate_leaf("contains", "Hello AegisAI World", "AegisAI") is True
    assert evaluator.evaluate_leaf("not_contains", "Hello World", "AegisAI") is True
    
    # Exists & Not exists
    assert evaluator.evaluate_leaf("exists", "Active", None) is True
    assert evaluator.evaluate_leaf("not_exists", None, None) is True
    
    # Type mismatch safety
    assert evaluator.evaluate_leaf("greater_than", None, 10) is False
