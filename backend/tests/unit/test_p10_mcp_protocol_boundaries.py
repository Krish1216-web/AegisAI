import pytest
from app.core.mcp.policy import ToolRiskPolicy, ToolRiskLevel, ToolPolicyDecision

def test_mcp_tool_risk_assessment_boundaries():
    # 1. Empty tool name
    res_empty = ToolRiskPolicy.assess_tool(name="")
    assert res_empty["risk_level"] == ToolRiskLevel.INVALID.value
    assert res_empty["policy_decision"] == ToolPolicyDecision.DENY.value
    
    # 2. Dangerous system execution keyword
    res_exec = ToolRiskPolicy.assess_tool(name="execute_system_shell", description="Executes shell scripts")
    assert res_exec["risk_level"] == ToolRiskLevel.RESTRICTED.value or res_exec["policy_decision"] == ToolPolicyDecision.REQUIRE_CONFIRMATION.value
    
    # 3. Benign safe tool
    res_safe = ToolRiskPolicy.assess_tool(name="get_weather_forecast", description="Returns weather forecast")
    assert res_safe["risk_level"] == ToolRiskLevel.SAFE.value
    assert res_safe["policy_decision"] == ToolPolicyDecision.ALLOW.value
