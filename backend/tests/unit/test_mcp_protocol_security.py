import pytest
from app.core.mcp.validation import MCPValidator
from app.core.mcp.base import MCPValidationError

def test_ssrf_and_private_subnet_uri_rejections():
    # 1. AWS metadata endpoint
    with pytest.raises(MCPValidationError, match="SSRF"):
        MCPValidator.validate_resource_uri("https://169.254.169.254/latest/meta-data")

    # 2. Localhost and loopback
    with pytest.raises(MCPValidationError, match="SSRF"):
        MCPValidator.validate_resource_uri("http://localhost:8080/admin")

    with pytest.raises(MCPValidationError, match="SSRF"):
        MCPValidator.validate_resource_uri("http://127.0.0.1:9200/_cat")

    # 3. Private IP ranges
    with pytest.raises(MCPValidationError, match="private/internal"):
        MCPValidator.validate_resource_uri("http://10.0.1.50/internal")

    with pytest.raises(MCPValidationError, match="private/internal"):
        MCPValidator.validate_resource_uri("http://192.168.1.1/router")

def test_file_uri_and_path_traversal_rejections():
    with pytest.raises(MCPValidationError, match="file://"):
        MCPValidator.validate_resource_uri("file:///etc/passwd")

    with pytest.raises(MCPValidationError, match="path traversal"):
        MCPValidator.validate_resource_uri("workspace://docs/../../secret.env")

def test_command_injection_characters_in_server_url():
    with pytest.raises(MCPValidationError, match="command injection"):
        MCPValidator.validate_server_url("http://server.com/api;rm -rf /")

    with pytest.raises(MCPValidationError, match="command injection"):
        MCPValidator.validate_server_url("http://server.com/api`whoami`")

def test_recursive_json_schema_depth_limit():
    # Construct schema exceeding depth limit 6
    deep_schema = {"type": "object", "properties": {}}
    curr = deep_schema["properties"]
    for i in range(8):
        curr["nested"] = {"type": "object", "properties": {}}
        curr = curr["nested"]["properties"]

    with pytest.raises(MCPValidationError, match="maximum nesting depth"):
        MCPValidator.validate_tool_input_schema(deep_schema)
