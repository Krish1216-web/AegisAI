import pytest
from app.core.mcp.validation import MCPValidator
from app.core.mcp.base import MCPValidationError
from app.models.mcp import MCPTransport

def test_validate_server_name_success():
    assert MCPValidator.validate_server_name("GitHub Server 1") == "GitHub Server 1"
    assert MCPValidator.validate_server_name("postgres-db_node.v1") == "postgres-db_node.v1"

def test_validate_server_name_rejections():
    with pytest.raises(MCPValidationError):
        MCPValidator.validate_server_name("")
    with pytest.raises(MCPValidationError):
        MCPValidator.validate_server_name("   ")
    with pytest.raises(MCPValidationError):
        MCPValidator.validate_server_name("A" * 101)
    with pytest.raises(MCPValidationError):
        MCPValidator.validate_server_name("Invalid;Name`rm -rf /`")

def test_validate_server_url_schemes():
    assert MCPValidator.validate_server_url("http://localhost:8000/sse") == "http://localhost:8000/sse"
    assert MCPValidator.validate_server_url("https://api.github.com/mcp") == "https://api.github.com/mcp"
    assert MCPValidator.validate_server_url("mock://test-server") == "mock://test-server"
    assert MCPValidator.validate_server_url("python -m server.py", transport=MCPTransport.STDIO) == "python -m server.py"

def test_validate_server_url_rejections():
    with pytest.raises(MCPValidationError):
        MCPValidator.validate_server_url("ftp://unsupported.domain/mcp")
    with pytest.raises(MCPValidationError):
        MCPValidator.validate_server_url("http://localhost:8000; rm -rf /")
    with pytest.raises(MCPValidationError):
        MCPValidator.validate_server_url("http://localhost:8000 | cat /etc/passwd")

def test_validate_metadata_size_limits():
    valid = {"tag": "prod", "env": 1}
    assert MCPValidator.validate_metadata(valid) == valid
    assert MCPValidator.validate_metadata(None) == {}
    
    # Oversized payload
    oversized = {"data": "x" * (70 * 1024)}
    with pytest.raises(MCPValidationError) as exc:
        MCPValidator.validate_metadata(oversized)
    assert "exceeds maximum size limit" in str(exc.value)

def test_validate_tool_input_schema():
    valid_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"}
        },
        "required": ["query"]
    }
    validated = MCPValidator.validate_tool_input_schema(valid_schema)
    assert validated["type"] == "object"
    assert "query" in validated["properties"]

def test_validate_tool_input_schema_depth_limit():
    # Deep nested structure
    deep = {}
    curr = deep
    for _ in range(8):
        curr["nested"] = {}
        curr = curr["nested"]
    
    with pytest.raises(MCPValidationError) as exc:
        MCPValidator.validate_tool_input_schema(deep)
    assert "maximum nesting depth" in str(exc.value)
