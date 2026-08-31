import enum
import re
from typing import Dict, Any, List, Optional, Tuple

class ToolRiskLevel(str, enum.Enum):
    SAFE = "safe"
    RESTRICTED = "restricted"
    INVALID = "invalid"

class ToolPolicyDecision(str, enum.Enum):
    ALLOW = "allow"
    REQUIRE_CONFIRMATION = "require_confirmation"
    DENY = "deny"

# Suspicious keywords that signal potential shell / system / destructive operations
RESTRICTED_KEYWORDS = [
    re.compile(r"(shell|exec|eval|system|subprocess|bash|powershell|cmd|terminal|spawn)", re.IGNORECASE),
    re.compile(r"(rm\s+-rf|format\s+disk|drop\s+database|truncate\s+table|delete_all)", re.IGNORECASE),
    re.compile(r"(dump_env|read_secrets|extract_token|steal_credentials|dump_memory)", re.IGNORECASE),
    re.compile(r"(socket|bind_port|reverse_shell|ssh_tunnel)", re.IGNORECASE)
]

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(previous|all)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"reveal\s+(system\s+prompt|credentials|passwords)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+dan\s+mode", re.IGNORECASE),
    re.compile(r"bypass\s+security", re.IGNORECASE),
]

class ToolRiskPolicy:
    """
    Evaluates discovered tool capabilities against deterministic safety rules,
    producing an explainable risk classification (SAFE, RESTRICTED, INVALID).
    """

    @classmethod
    def assess_tool(
        cls,
        name: str,
        description: Optional[str] = None,
        input_schema: Optional[Dict[str, Any]] = None,
        meta_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        risk_reasons: List[str] = []
        clean_name = (name or "").strip()
        clean_desc = (description or "").strip()

        # 1. Validation sanity check
        if not clean_name:
            return {
                "risk_level": ToolRiskLevel.INVALID.value,
                "policy_decision": ToolPolicyDecision.DENY.value,
                "risk_reasons": ["Tool name cannot be empty."]
            }

        if input_schema is not None and not isinstance(input_schema, dict):
            return {
                "risk_level": ToolRiskLevel.INVALID.value,
                "policy_decision": ToolPolicyDecision.DENY.value,
                "risk_reasons": ["Tool input_schema must be a valid JSON object."]
            }

        # 2. Check for restricted execution keywords in tool name
        for pattern in RESTRICTED_KEYWORDS:
            if pattern.search(clean_name):
                risk_reasons.append(f"Tool name contains restricted system/execution keyword: '{pattern.pattern}'")

        # 3. Check for restricted execution keywords in description
        for pattern in RESTRICTED_KEYWORDS:
            if pattern.search(clean_desc):
                risk_reasons.append(f"Tool description indicates potential system-level or destructive capability")
                break

        # 4. Check schema property names for dangerous parameters
        if input_schema and isinstance(input_schema, dict):
            props = input_schema.get("properties", {})
            if isinstance(props, dict):
                if len(props) > 50:
                    risk_reasons.append("Tool input schema exceeds maximum allowed property count (50).")
                for prop_name, prop_def in props.items():
                    for pattern in RESTRICTED_KEYWORDS:
                        if pattern.search(prop_name):
                            risk_reasons.append(f"Schema property '{prop_name}' specifies a restricted parameter.")
                            break

        # 5. Check metadata tags
        if meta_data and isinstance(meta_data, dict):
            for k, v in meta_data.items():
                if isinstance(v, str) and any(pattern.search(v) for pattern in RESTRICTED_KEYWORDS):
                    risk_reasons.append(f"Metadata tag '{k}' contains restricted indicators.")

        # Determine final risk level and policy decision
        if any("schema exceeds" in r for r in risk_reasons):
            return {
                "risk_level": ToolRiskLevel.INVALID.value,
                "policy_decision": ToolPolicyDecision.DENY.value,
                "risk_reasons": risk_reasons
            }

        if risk_reasons:
            return {
                "risk_level": ToolRiskLevel.RESTRICTED.value,
                "policy_decision": ToolPolicyDecision.REQUIRE_CONFIRMATION.value,
                "risk_reasons": risk_reasons
            }

        return {
            "risk_level": ToolRiskLevel.SAFE.value,
            "policy_decision": ToolPolicyDecision.ALLOW.value,
            "risk_reasons": []
        }

class PromptInjectionDetector:
    """
    Validates that prompt injection keywords in tool metadata are neutralized
    and treated strictly as inert data strings without altering AI agent instructions.
    """
    @classmethod
    def contains_injection_payload(cls, text: Optional[str]) -> bool:
        if not text:
            return False
        return any(pattern.search(text) for pattern in PROMPT_INJECTION_PATTERNS)
