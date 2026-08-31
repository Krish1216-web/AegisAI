import pytest
from app.core.mcp.validation import MCPValidator
from app.core.mcp.base import MCPValidationError

def test_valid_tool_schema_validation():
    valid_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword"},
            "max_results": {"type": "integer", "default": 10}
        },
        "required": ["query"]
    }
    validated = MCPValidator.validate_tool_input_schema(valid_schema)
    assert validated["type"] == "object"
    assert "query" in validated["properties"]
    assert validated["required"] == ["query"]

def test_malformed_tool_schema_rejected():
    with pytest.raises(MCPValidationError) as exc:
        MCPValidator.validate_tool_input_schema("not a dictionary")
    assert "must be a JSON object dictionary" in str(exc.value)

def test_tool_schema_depth_limit():
    # Build deep 8-level nesting
    deep_schema = {"type": "object"}
    current = deep_schema
    for i in range(8):
        current["properties"] = {f"level_{i}": {"type": "object"}}
        current = current["properties"][f"level_{i}"]

    with pytest.raises(MCPValidationError) as exc:
        MCPValidator.validate_tool_input_schema(deep_schema)
    assert "exceeds maximum nesting depth" in str(exc.value)

def test_tool_name_and_metadata_validation():
    assert MCPValidator.validate_server_name("valid_tool_123") == "valid_tool_123"
    with pytest.raises(MCPValidationError):
        MCPValidator.validate_server_name("")
    with pytest.raises(MCPValidationError):
        MCPValidator.validate_server_name("invalid/tool/name#$")
