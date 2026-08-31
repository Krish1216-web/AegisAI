import re
from typing import Dict, Any, List, Optional, Union, Tuple
from loguru import logger

MAX_CONDITION_NESTING_DEPTH = 3
MAX_CONDITIONS_PER_GROUP = 10
MAX_OPERAND_LENGTH = 10000

SUPPORTED_LOGIC_OPERATORS = {"AND", "OR", "NOT"}

SUPPORTED_COMPARISON_OPERATORS = {
    "equals",
    "not_equals",
    "greater_than",
    "less_than",
    "greater_or_equal",
    "less_or_equal",
    "contains",
    "not_contains",
    "exists",
    "not_exists",
    "in",
    "not_in",
    "starts_with",
    "ends_with"
}

class ConditionEvaluationError(Exception):
    """Raised when condition evaluation fails due to illegal structure or invalid operands."""
    pass

class ConditionEvaluator:
    """
    Deterministic, type-safe condition evaluator for AegisAI Workflows.
    Supports single leaf comparisons, compound logic groups (AND / OR / NOT),
    nested condition trees up to bounded depth, and structured evaluation metadata.
    Zero eval(), exec(), or arbitrary dynamic code execution.
    """

    @classmethod
    def validate_structure(
        cls,
        condition: Optional[Dict[str, Any]],
        depth: int = 1,
        max_depth: int = MAX_CONDITION_NESTING_DEPTH
    ) -> List[str]:
        """
        Validates condition dictionary structure before workflow activation.
        Returns a list of error messages (empty if valid).
        """
        if condition is None:
            return []

        if not isinstance(condition, dict):
            return ["Condition must be a JSON object."]

        errors = []

        if depth > max_depth:
            return [f"Condition nesting depth exceeds maximum allowed depth of {max_depth}."]

        # Check if default edge indicator
        if condition.get("is_default") is True:
            return []

        # 1. Condition Group (AND / OR / NOT)
        if "logic" in condition or "conditions" in condition:
            logic = str(condition.get("logic", "AND")).upper()
            if logic not in SUPPORTED_LOGIC_OPERATORS:
                errors.append(f"Invalid logic operator '{logic}'. Must be one of: {', '.join(SUPPORTED_LOGIC_OPERATORS)}.")

            children = condition.get("conditions")
            if children is None:
                errors.append("Condition group must define a 'conditions' array.")
            elif not isinstance(children, list):
                errors.append("'conditions' must be a list.")
            elif len(children) == 0:
                errors.append("Condition group 'conditions' list cannot be empty.")
            elif len(children) > MAX_CONDITIONS_PER_GROUP:
                errors.append(f"Condition group contains {len(children)} items, exceeding maximum of {MAX_CONDITIONS_PER_GROUP}.")
            else:
                if logic == "NOT" and len(children) != 1:
                    errors.append(f"Logic operator 'NOT' requires exactly 1 child condition, got {len(children)}.")

                for idx, child in enumerate(children):
                    child_errors = cls.validate_structure(child, depth=depth + 1, max_depth=max_depth)
                    for err in child_errors:
                        errors.append(f"Child condition [{idx}]: {err}")

            return errors

        # 2. Single Leaf Condition
        operator = str(condition.get("operator", "equals")).lower()
        if operator not in SUPPORTED_COMPARISON_OPERATORS:
            errors.append(f"Invalid comparison operator '{operator}'. Must be one of: {', '.join(sorted(SUPPORTED_COMPARISON_OPERATORS))}.")

        # Operator-specific operand validation
        if operator in ("exists", "not_exists"):
            if "left" not in condition and "expression" not in condition:
                errors.append(f"Operator '{operator}' requires a 'left' operand.")
        else:
            if "left" not in condition and "expression" not in condition:
                errors.append(f"Operator '{operator}' requires a 'left' operand.")
            if "right" not in condition:
                errors.append(f"Operator '{operator}' requires a 'right' operand.")

        return errors

    @classmethod
    def _coerce_types(cls, left: Any, right: Any) -> Tuple[Any, Any]:
        """
        Safely attempts non-destructive type normalization for comparisons.
        """
        # String booleans
        if isinstance(left, str):
            if left.lower() == "true":
                left = True
            elif left.lower() == "false":
                left = False
            elif left.isdigit():
                left = int(left)
            else:
                try:
                    left = float(left)
                except ValueError:
                    pass

        if isinstance(right, str):
            if right.lower() == "true":
                right = True
            elif right.lower() == "false":
                right = False
            elif right.isdigit():
                right = int(right)
            else:
                try:
                    right = float(right)
                except ValueError:
                    pass

        return left, right

    @classmethod
    def evaluate_leaf(
        cls,
        operator: str,
        left: Any,
        right: Any
    ) -> bool:
        """
        Evaluates a single leaf condition in a type-safe manner.
        """
        op = operator.lower()

        # Exists / Not Exists
        if op == "exists":
            return left is not None and left != ""
        elif op == "not_exists":
            return left is None or left == ""

        # Normalize types for comparison
        left_val, right_val = cls._coerce_types(left, right)

        if op == "equals":
            # Direct value equality
            if type(left_val) == type(right_val):
                return left_val == right_val
            return str(left_val).lower() == str(right_val).lower() if (isinstance(left_val, bool) or isinstance(right_val, bool)) else left_val == right_val

        elif op == "not_equals":
            return not cls.evaluate_leaf("equals", left, right)

        elif op == "greater_than":
            try:
                return float(left_val) > float(right_val)
            except (ValueError, TypeError):
                return False

        elif op == "less_than":
            try:
                return float(left_val) < float(right_val)
            except (ValueError, TypeError):
                return False

        elif op == "greater_or_equal":
            try:
                return float(left_val) >= float(right_val)
            except (ValueError, TypeError):
                return False

        elif op == "less_or_equal":
            try:
                return float(left_val) <= float(right_val)
            except (ValueError, TypeError):
                return False

        elif op == "contains":
            if left is None or right is None:
                return False
            if isinstance(left, list):
                return right in left or str(right) in [str(x) for x in left]
            if isinstance(left, dict):
                return str(right) in left
            return str(right).lower() in str(left).lower()

        elif op == "not_contains":
            return not cls.evaluate_leaf("contains", left, right)

        elif op == "in":
            if right is None or left is None:
                return False
            if isinstance(right, list):
                return left in right or str(left) in [str(x) for x in right]
            if isinstance(right, dict):
                return str(left) in right
            return str(left).lower() in str(right).lower()

        elif op == "not_in":
            return not cls.evaluate_leaf("in", left, right)

        elif op == "starts_with":
            if left is None or right is None:
                return False
            return str(left).startswith(str(right))

        elif op == "ends_with":
            if left is None or right is None:
                return False
            return str(left).endswith(str(right))

        return False

    @classmethod
    def evaluate(
        cls,
        condition: Optional[Dict[str, Any]],
        context: Any,
        depth: int = 1,
        max_depth: int = MAX_CONDITION_NESTING_DEPTH
    ) -> Dict[str, Any]:
        """
        Evaluates condition dictionary against WorkflowExecutionContext.
        Returns a dictionary with result, details, and evaluation metadata.
        """
        if not condition or not isinstance(condition, dict):
            return {
                "result": True,
                "logic": "NONE",
                "evaluated_conditions": 0,
                "details": []
            }

        # Check default fallback edge
        if condition.get("is_default") is True:
            return {
                "result": True,
                "is_default": True,
                "logic": "DEFAULT",
                "evaluated_conditions": 0,
                "details": []
            }

        if depth > max_depth:
            logger.warning(f"Condition depth exceeded {max_depth}; defaulting to false.")
            return {
                "result": False,
                "error": "MAX_DEPTH_EXCEEDED",
                "evaluated_conditions": 0,
                "details": []
            }

        # 1. Condition Group (AND / OR / NOT)
        if "logic" in condition or "conditions" in condition:
            logic = str(condition.get("logic", "AND")).upper()
            children = condition.get("conditions", [])

            evaluated_children = []
            results = []

            for child in children:
                res_child = cls.evaluate(child, context, depth=depth + 1, max_depth=max_depth)
                evaluated_children.append(res_child)
                results.append(res_child.get("result", False))

            if logic == "AND":
                final_result = all(results) if results else True
            elif logic == "OR":
                final_result = any(results) if results else False
            elif logic == "NOT":
                final_result = not results[0] if results else False
            else:
                final_result = all(results)

            return {
                "result": final_result,
                "logic": logic,
                "evaluated_conditions": len(children),
                "details": evaluated_children
            }

        # 2. Leaf Condition
        left_raw = condition.get("left") if "left" in condition else condition.get("expression")
        operator = str(condition.get("operator", "equals")).lower()
        right_raw = condition.get("right")

        # Resolve variables using WorkflowExecutionContext
        left = context.resolve_expression(left_raw) if isinstance(left_raw, str) else left_raw
        right = context.resolve_expression(right_raw) if isinstance(right_raw, str) else right_raw

        leaf_result = cls.evaluate_leaf(operator, left, right)

        return {
            "result": leaf_result,
            "operator": operator,
            "left": left,
            "right": right,
            "evaluated_conditions": 1,
            "details": []
        }
